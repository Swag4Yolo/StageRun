from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from lib.tofino.constants import *
from lib.controller.constants import P1_TABLE

logger = logging.getLogger(__name__)

# importa os teus tipos reais
from .types import (
    MicroGraph,
    MicroNode,
    MicroEdge,
    MicroInstruction,
    MicroEffect
)

# ----------------------------
# Estruturas auxiliares
# ----------------------------

@dataclass
class PlannerStats:
    stages_used: int = 0
    total_nodes: int = 0
    total_flows: int = 0
    write_phases_inserted: int = 0
    wp_reserved: Dict[int, Set[int]] = field(default_factory=dict)



@dataclass
class PlanningResult:
    graphs: List[MicroGraph]
    stats: PlannerStats | None = None

class PlannerError(Exception):
    pass

# ============================
#        PLANNER
# ============================
class PlannerError(Exception):
    pass


class Planner:
    def __init__(self, isa: Dict[str, Any]):
        self.isa = isa
        self.stats = PlannerStats()
        self._flow_counter = 0  # global flow_id counter
        self._internal_node_counter = {}
        self._pkt_id = 0
        self._wp_reserved: Dict[int, Set[int]] = {}
        self._occupied_stages: Dict[int, set[int]] = {} 

    def _new_flow_id(self) -> int:
        """Generates a globally unique flow_id."""
        self._flow_counter += 1
        return self._flow_counter
    
    def _new_internal_id(self, graph_id) -> int:
        """Generates a unique internal node ID for synthetic nodes (write-phase, recirc, etc.)."""
        self._internal_node_counter[graph_id] += 1
        return self._internal_node_counter[graph_id]
    
    def _new_pkt_id(self) -> int:
        """Generates a globally unique pkt_id to be used by default_action."""
        self._pkt_id += 1
        return self._pkt_id

    # ============================================================
    # PUBLIC
    # ============================================================

    def plan(self, micro_graphs: List[MicroGraph], pid: int) -> PlanningResult:
        """
        Plan all graphs:
          - assigns unique flow_id per graph
          - allocates stages/tables respecting ISA
          - handles recirculation & IFs
          - inserts and re-allocates write-phases
        """
        planned_graphs = []

        for g in micro_graphs:
            # 0. Init values
            self._internal_node_counter[g.graph_id] = len(g.nodes)
            base_flow_id = self._new_flow_id()

            # 1. Add PreFilter Keys
            if g.keys:
                pkt_id = self._new_pkt_id()
                g.keys['kwargs']['program_id'] = pid
                g.keys['kwargs']['pkt_id'] = pkt_id
                # TODO: implement {ni_f1, ni_f2} in kwargs
                g.keys['kwargs']['ni_f1'] = base_flow_id
                g.keys['kwargs']['ni_f2'] = base_flow_id

            
            # 2. Default Action
            if g.default_action:
                g.default_action['kwargs']['pkt_id'] = pkt_id

            # 3. Nodes
            for n in g.nodes.values():
                n.flow_id = base_flow_id
                n.instr.kwargs["program_id"] = pid

            # Extra: Assegurar seq linear - necesario?
            # for edge in g.edges:
            #     if edge.dep == "DATA":
            #         src = g.nodes[edge.src]
            #         dst = g.nodes[edge.dst]
            #         src.instr.kwargs.setdefault("instr_id", dst.flow_id)


            self._allocate_stages(g, pid)
            planned_graphs.append(g)

            if __debug__:
                logger.debug(f"Number of reserved WP: {self._wp_reserved}")

        return PlanningResult(planned_graphs, PlannerStats(write_phases_inserted=self._wp_reserved))
    # ============================================================
    # CORE
    # ============================================================
    def _allocate_stages(self, g: MicroGraph, pid: int):
        """
        Greedy planner:
        - Tenta colocar cada micro-instruction num stage permitido pelo ISA.
        - Insere write_phases quando há RAW dependencies (write→read).
        - Evita colisões globais de write phases (via _wp_reserved).
        """

        # Estado global
        pending_writes: Dict[str, int] = {}   # var -> stage
        current_stage = 0
        flow_id = self._new_flow_id()         # flow_id inicial deste grafo

        order = self._topo_sort(g)

        for idx, node in enumerate(order):
            op = node.instr.name
            placed = False

            # --- 1️⃣ Determinar candidatas no ISA ---
            candidate_ops = [op]
            if node.instr.alternative:
                candidate_ops.append(node.instr.alternative)

            # --- ⚙️ IFs (decide) — usar slots e gerar flows ---
            if self._is_decide(node):
                # Preenche slot_map e flow_ids de branches
                self._assign_conditional_slots(node)
                self._assign_branch_flow_ids(g, node)

                slot_map = node.instr.kwargs.get("slot_map", {})
                reads = getattr(node.effect, "reads", set()) or set()

                # Decide qual micro-instrução física usar
                if len(reads) == 2:
                    # Verifica se ambas as variáveis são mapeadas para slots válidos
                    vars_mapped = all(v in slot_map for v in reads)
                    if vars_mapped:
                        # Ambas as variáveis estão em v1,v2,v3,v4 → between_vars
                        candidate_ops = [
                            "speculative_conditional_between_vars",
                            "conditional_between_vars",
                        ]
                    else:
                        # Uma variável e uma constante
                        candidate_ops = [
                            "speculative_conditional_v1_v2",
                            "conditional_v1_v2",
                            "speculative_conditional_v3_v4",
                            "conditional_v3_v4",
                        ]
                elif len(reads) == 1:
                    # Um único comparando com constante
                    candidate_ops = [
                        "speculative_conditional_v1_v2",
                        "conditional_v1_v2",
                        "speculative_conditional_v3_v4",
                        "conditional_v3_v4",
                    ]
                else:
                    # fallback — IF vazio ou inesperado
                    candidate_ops = [
                        "conditional_v1_v2",
                        "speculative_conditional_v1_v2",
                    ]


            # --- 2️⃣ Escolher stage / flow disponível (compatível com StageRunEngine ISA) ---
            for stage_name, flows in self.isa["pipeline"].items():
                # extrai o índice numérico do stage (s1→1, s2→2, ...)
                s_idx = int(stage_name.lstrip("s"))
                if s_idx < current_stage:
                    continue  # nunca voltamos atrás

                for flow_name, flow_data in flows.items():
                    # junta todas as listas de instruções possíveis

                    for table_name, instr_list in flow_data.items():
                        if isinstance(instr_list, list):
                            if any(cand in instr_list for cand in candidate_ops):
                                node.allocated_stage = s_idx
                                node.allocated_flow = flow_name
                                node.allocated_table = table_name   # agora guarda o correto
                                node.flow_id = flow_id
                                # apenas a tabela 1 não tem next_flow_id
                                if table_name not in P1_TABLE:
                                    node.instr.kwargs["instr_id"] = flow_id
                                placed = True
                                current_stage = s_idx

                                # # --- Extra rule: PADTTERN (initialize_pad_ni) forces recirculation ---
                                # if node.instr.name == "initialize_pad_ni":
                                #     if __debug__:
                                #         logger.debug(f"[Planner][Recirc] Forced recirculation after PADTTERN (node {node.id})")
                                #     # 1️⃣ Inserir recirculação imediatamente
                                #     new_flow = self._insert_recirc_before(g=g, node=node, pid=pid, prev_flow_id=node.flow_id)

                                #     # 2️⃣ Propagar o novo flow_id para as instruções seguintes
                                #     self._propagate_flow_id_forward(g=g, start_node=node, new_flow_id=new_flow)

                                #     # 3️⃣ Reiniciar a contagem de stages (recirculação volta ao início do pipeline)
                                #     current_stage = 0
                                #     flow_id = new_flow
                                # break

                    if placed:
                        # if node.instr.name not in self.isa["pipeline"][f"s{node.allocated_stage}"][node.allocated_flow][node.allocated_table]:
                        #     raise PlannerError(
                        #         f"Inconsistent ISA allocation: {node.instr.name} not in "
                        #         f"{node.allocated_flow}/{node.allocated_table} of stage s{node.allocated_stage}"
                        #     )
                        break
                if placed:
                    break

            # --- 3️⃣ Caso não tenha sido possível colocar (recirculação) ---
            if not placed:
                # s_back = max(0, current_stage - 1)
                # f_back = flow_id

                # cria recirculação
                new_flow = self._insert_recirc_before(g, node, pid, flow_id)
                #), s_back, f_back)
                flow_id = new_flow  # passa a usar o novo flow_id
                node.flow_id = new_flow

                # ⚙️ propagar para os próximos nós (DATA edges)
                self._propagate_flow_id_forward(g, start_node=node, new_flow_id=new_flow)

                # ⚙️ reset stages (recomeça no início da pipeline)
                current_stage = 0

                # ⚙️ manter reservas globais — não sobrescreve write phases existentes
                current_stage = self._is_stage_free(pid, current_stage + 1)

                # ⚙️ tentar novamente colocar o nó neste novo fluxo
                placed = False
                for stage_name, flows in self.isa["pipeline"].items():
                    s_idx = int(stage_name.lstrip("s"))
                    if s_idx < current_stage:
                        continue

                    for flow_name, flow_data in flows.items():
                        instr_sets = []
                        for key, instr_list in flow_data.items():
                            if isinstance(instr_list, list):
                                instr_sets.extend(instr_list)

                        if any(cand in instr_sets for cand in candidate_ops):
                            node.allocated_stage = s_idx
                            node.allocated_flow = flow_name
                            node.allocated_table = key
                            node.flow_id = flow_id
                            placed = True
                            current_stage = s_idx
                            break
                    if placed:
                        break

                if not placed:
                    raise PlannerError(f"Could not re-place instruction '{op}' even after recirculation")

            # --- 5️⃣ Segurança: erro se nada foi colocado ---
            if not placed:
                raise PlannerError(f"Instruction '{op}' could not be placed in pipeline")

            # avança stage para próxima instrução
            current_stage = max(current_stage, node.allocated_stage + 1)

        # --- 6️⃣ Inserir write-phases globais no fim (fallback) ---
        self._insert_global_write_phases(g=g, ordered_nodes=order, pid=pid)

    # ============================================================
    # HELPERS: ISA pick / topo / recirc / write-phase / decide
    # ============================================================

    # # === ISA helpers (v1.9) ======================================

    # def _iter_stage_defs(self) -> List[Tuple[int, str, str, List[str]]]:
    #     """
    #     Yield (stage_index, flow_name, table_name, instr_list)
    #     for all (s1..s10) x (f1,f2) x (tables).
    #     Tables present per stage/flow depend on the JSON keys.  :contentReference[oaicite:2]{index=2}
    #     """
    #     pipe = self.isa.get("pipeline", {})
    #     out = []
    #     for s_idx in range(1, 11):
    #         s_key = f"s{s_idx}"
    #         s = pipe.get(s_key, {})
    #         for flow in ("f1", "f2"):
    #             f = s.get(flow, {})
    #             # s10: 'multi_instr_speculative'; s1: 'instructions_p1'; s2..s9: 'instructions_p2' + 'instructions_speculative'
    #             # for table in ("instructions_p1", "instructions_p2", "instructions_speculative", "multi_instr_speculative"):
    #             for table in f:
    #                 instrs = f[table]
    #                 out.append((s_idx, flow, table, [x.lower() for x in instrs]))
    #     return out

    # def _find_forward(self, names: List[str], start_stage: int) -> Optional[Tuple[int,str,str,str]]:
    #     """
    #     Search forward from start_stage for any of 'names'.
    #     Returns (stage_index, flow, table_name, used_name) or None.
    #     """
    #     names = [n.lower() for n in names if n]
    #     for (s_idx, flow, table, instrs) in self._iter_stage_defs():
    #         if s_idx < max(1, start_stage):  # stages start at 1
    #             continue
    #         for nm in names:
    #             if nm in instrs:
    #                 return (s_idx, flow, table, nm)
    #     return None

    # def _find_backward(self, names: List[str], start_before: int) -> Optional[Tuple[int,str,str,str]]:
    #     """
    #     Search backward from start_before-1 down to s1.
    #     Returns (stage_index, flow, table_name, used_name) or None.
    #     """
    #     names = [n.lower() for n in names if n]
    #     for (s_idx, flow, table, instrs) in sorted(self._iter_stage_defs(), key=lambda x: -x[0]):
    #         if s_idx >= start_before:
    #             continue
    #         for nm in names:
    #             if nm in instrs:
    #                 return (s_idx, flow, table, nm)
    #     return None

    # def _reallocate_from(self, g: MicroGraph, start_node: MicroNode, start_stage: int) -> None:
    #     """
    #     Re-allocate stages from 'start_node' forward (DATA order) using ISA rules again.
    #     """
    #     order = self._topo_sort(g)
    #     started = False
    #     current_stage = start_stage

    #     for node in order:
    #         if not started:
    #             if node.id == start_node.id:
    #                 started = True
    #             else:
    #                 continue

    #         # write-phase node: força “tabela” simbólica
    #         if str(getattr(node.instr, "name", "")).lower() == "write_phase":
    #             node.allocated_stage = current_stage
    #             node.allocated_table = "write_phase"
    #             node.allocated_flow  = getattr(node, "allocated_flow", "f1")
    #             current_stage += 1
    #             continue

    #         cand_names = self._candidate_ops_for_node(node)
    #         fwd = self._find_forward(cand_names, current_stage)
    #         if fwd is None:
    #             # tentar uma recirculação local (pouco comum neste ponto)
    #             back = self._find_backward(cand_names, start_before=current_stage)
    #             if back is None:
    #                 raise PlannerError(f"Reallocation failed for node {node.id} ({node.instr.name}).")
    #             s_idx, flow, table, used_name = back
    #         else:
    #             s_idx, flow, table, used_name = fwd

    #         node.allocated_stage = s_idx
    #         node.allocated_table = f"{flow}.{table}"
    #         node.allocated_flow  = flow
    #         current_stage = max(current_stage, s_idx + 1)

    def _is_decide(self, node) -> bool:
        return str(getattr(node.instr, "name", "")).lower() == "decide"

    # def _isa_pick_table(self, node, start_from_stage: int):
    #     """
    #     Procura em stages >= start_from_stage uma tabela que suporte
    #     node.instr.name; se não houver, tenta .alternative.
    #     Retorna (stage, table_name, used_instr_name) ou None.
    #     """
    #     name = node.instr.name.lower()
    #     alt  = (getattr(node.instr, "alternative", None) or "").lower()

    #     stages = self.isa.get("pipeline", {}).get("stages", [])
    #     for s in range(max(0, start_from_stage), len(stages)):
    #         for t in stages[s].get("tables", []):
    #             instrs = [i.lower() for i in t.get("instrs", [])]
    #             if name in instrs:
    #                 return s, t["name"], node.instr.name
    #             if alt and alt in instrs:
    #                 return s, t["name"], getattr(node.instr, "alternative")
    #     return None

    # def _isa_pick_table_backward(self, node, start_from: int):
    #     """
    #     Procura “para trás” (stage decrescentes) — usado antes de recirculação.
    #     Retorna (stage, table_name, used_instr_name) ou None.
    #     """
    #     name = node.instr.name.lower()
    #     alt  = (getattr(node.instr, "alternative", None) or "").lower()

    #     stages = self.isa.get("pipeline", {}).get("stages", [])
    #     for s in range(start_from, -1, -1):
    #         for t in stages[s].get("tables", []):
    #             instrs = [i.lower() for i in t.get("instrs", [])]
    #             if name in instrs:
    #                 return s, t["name"], node.instr.name
    #             if alt and alt in instrs:
    #                 return s, t["name"], getattr(node.instr, "alternative")
    #     return None
    
    def _assign_conditional_slots(self, decide_node: MicroNode) -> None:
        reads = []
        if isinstance(decide_node.instr.kwargs, dict):
            reads = list(decide_node.instr.kwargs.get("reads", []))
        slots = ["v1", "v2", "v3", "v4"]
        slot_map = {}
        si = 0
        for var in reads:
            if var not in slot_map and si < len(slots):
                slot_map[var] = slots[si]
                si += 1
        if isinstance(decide_node.instr.kwargs, dict):
            decide_node.instr.kwargs["slot_map"] = slot_map

    def _assign_branch_flow_ids(self, g, decide_node):
        cond_ir = decide_node.instr.kwargs.get("cond_ir", {})
        n = len(cond_ir.get("branches", []))
        labels = [f"branch_{i}" for i in range(n)]
        if cond_ir.get("has_else", False):
            labels.append("else")

        branch_ids = {}

        for lbl in labels:
            heads = [e.dst for e in g.edges if e.dep == "CONTROL" and e.src == decide_node.id and e.label == lbl]
            if not heads:
                continue
            new_flow = self._new_flow_id()
            branch_ids[lbl] = new_flow
            for h in heads:
                head_node = g.nodes[h]
                head_node.flow_id = new_flow
                # 🟢 primeira instrução do branch aponta para o novo flow_id
                head_node.instr.kwargs["instr_id"] = new_flow
                self._propagate_flow_id(g, start_node_id=h, new_flow_id=new_flow)

        # guarda referência nos kwargs do decide
        decide_node.instr.kwargs["branch_instr_ids"] = branch_ids

    def _topo_sort(self, g) -> List[MicroNode]:
        """
        Topological order only by DATA dependencies.
        CONTROL edges are ignored (they represent branches).
        Returns a list of MicroNode in causal order.
        """
        indeg = {nid: 0 for nid in g.nodes}
        adj = {nid: [] for nid in g.nodes}

        for e in g.edges:
            if e.dep == "DATA" and e.src in g.nodes and e.dst in g.nodes:
                adj[e.src].append(e.dst)
                indeg[e.dst] += 1

        Q = [nid for nid, d in indeg.items() if d == 0]
        ordered_ids = []
        while Q:
            nid = Q.pop(0)
            ordered_ids.append(nid)
            for nxt in adj[nid]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    Q.append(nxt)

        # fallback: nós que ficaram fora por ciclos/isolamento
        for nid in g.nodes:
            if nid not in ordered_ids:
                ordered_ids.append(nid)

        return [g.nodes[nid] for nid in ordered_ids]

    def _insert_recirc_before(self, g: MicroGraph, node: MicroNode, pid: int, prev_flow_id: int) -> int:
        """
        Insere um micro-nó de recirculação imediatamente antes de 'node'.
        - cria MicroNode(instr='pos_filter_recirc_same_pipe', kwargs=...)
        - reencaminha arestas que apontavam para 'node' para o novo nó
        - liga novo nó -> node (DATA)
        - gera novo flow_id e devolve-o
        """
        rec_id = self._new_internal_id(g.graph_id)
        new_flow_id = self._new_flow_id()

        rec_instr = MicroInstruction(
            name="pos_filter_recirc_same_pipe",
            kwargs={"program_id": pid, "next_flow_id": new_flow_id}
        )
        rec_node = MicroNode(
            id=rec_id, 
            instr=rec_instr, 
            graph_id=g.graph_id, 
            allocated_table="recirculation_t",
            flow_id=prev_flow_id,
            effect=MicroEffect(),
            )
        g.nodes[rec_id] = rec_node

        # redirect edges arriving to node
        for e in g.edges:
            if e.dst == node.id:
                e.dst = rec_id
                # # update instr_id of the predecessor to point to new flow
                # pred_node = g.nodes[e.src]
                # pred_node.instr.kwargs["instr_id"] = new_flow_id
                # pred_node.instr.kwargs["instr_id"] = self._new_flow_id()

        # link recirc → node
        g.edges.append(MicroEdge(src=rec_id, dst=node.id, dep="DATA"))

        # new_flow = rec_node.instr.kwargs["instr_id"]
        return new_flow_id

    def _is_decide(self, node: MicroNode) -> bool:
        return str(getattr(node.instr, "name", "")).lower() == "decide"

    def _candidate_ops_for_node(self, node: MicroNode) -> List[str]:
        """
        Primary + alternative candidates for allocation.
        For IF/decide, expand to the ISA speculative conditionals.  :contentReference[oaicite:4]{index=4}
        """
        name  = str(node.instr.name)
        alt   = getattr(node.instr, "alternative", None)
        if self._is_decide(node):
            # keep all three candidates; Planner/Installer decidirá com base no slot_map/cond_ir
            # TODO: it cannot return all three nodes
            return [
                "speculative_conditional_v1_v2",
                "speculative_conditional_v3_v4",
                "speculative_conditional_between_vars",
            ]
        out = [name]
        if alt:
            out.append(alt)
        return out


    def _propagate_flow_id_forward(self, g: MicroGraph, start_node: MicroNode, new_flow_id: int):
        """Propaga o novo flow_id para todos os nós seguintes via DATA edges."""
        visited = set()
        stack = [start_node.id]
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            node = g.nodes[nid]
            node.flow_id = new_flow_id
            for e in g.edges:
                if e.src == nid and e.dep == "DATA":
                    stack.append(e.dst)


    # ==========================================================
    #  WRITE PHASE MANAGEMENT
    # ==========================================================

    # def _insert_global_write_phases(self, g: MicroGraph, ordered_nodes: List[MicroNode], pid: int) -> None:
    #     """
    #     Scans the micro-graph and inserts write-phase nodes wherever dependencies
    #     between writes and subsequent reads require a memory synchronization.

    #     Uses a greedy approach: first write followed by read in next stage.
    #     """
    #     if __debug__:
    #         logger.debug(f"[Planner] Inserting global write-phases for graph '{g.graph_id}'")
    #         logger.debug(f"[Planner][Order] → {[n.id for n in ordered_nodes]}")


    #     current_stage = 0
    #     # nodes_sorted = sorted(g.nodes.values(), key=lambda n: n.id)

    #     for node in ordered_nodes:
    #         stage_val = getattr(node, "allocated_stage", None)
    #         op = getattr(node.instr, "name", "UNKNOWN")

    #         if stage_val is None:
    #             # skip nodes without a stage (e.g. recirculations)
    #             continue

    #         needs_wp = self._needs_write_phase(node=node, ordered_nodes=ordered_nodes)

    #         if __debug__:
    #             logger.debug(f"[Planner][Check] node={node.id} op={op} stage={stage_val} needs_wp={needs_wp}")

    #         if needs_wp:
    #             wp_stage = self._wp_next_free(pid, stage_val + 1)
    #             self._wp_reserve(pid, wp_stage)
    #             self._insert_write_phase_between(g, node, pid, wp_stage)
                
    #             if __debug__:
    #                 logger.debug(f"[Planner][Insert] Added write-phase after node {node.id} at stage {wp_stage}")

    #         current_stage = max(current_stage, stage_val + 1)

    #     # Debug summary
    #     wp_nodes = [n for n in g.nodes.values() if "write_phase" in getattr(n.instr, "name", "")]

    #     if __debug__:
    #         logger.debug(f"[Planner][Summary] total write-phases inserted: {len(wp_nodes)}")


    def _insert_global_write_phases(self, g: MicroGraph, ordered_nodes: List[MicroNode], pid: int) -> None:
        """
        Inserir write_phase_t depois de dependências write→read.
        Evita stages já ocupados por instruções (globais por programa).
        """
        logger.debug(f"[Planner] Inserting global write-phases for graph '{g.graph_id}'")

        # order = self._topo_sort(g)
        pending_writes: Dict[str, int] = {}
        inserted_wp = 0

        # Pré-carregar 'occupied' com as alocações deste grafo também
        # (como segurança, no caso de _mark_occupied ainda não ter sido chamado em todos)
        for n in g.nodes.values():
            if getattr(n, "allocated_stage", None) is not None:
                self._mark_occupied(pid, n.allocated_stage)

        for node in ordered_nodes:
            stage = getattr(node, "allocated_stage", None)
            if stage is None:
                continue

            eff = getattr(node, "effect", None)
            if not eff:
                continue

            reads = eff.reads or set()
            writes = eff.writes or set()

            # 1) detetar dependências write→read
            dirty_reads = {v for v in reads if v in pending_writes}
            if dirty_reads:
                last_dirty_stage = max(pending_writes[v] for v in dirty_reads)

                # bloquear stages já ocupados por este programa (globais) e reservas de WP
                blocked: set[int] = set()  # (podes adicionar aqui bloqueios específicos do grafo, se quiseres)
                wp_stage = self._wp_next_free(pid, last_dirty_stage + 1, g.graph_id, blocked=blocked)

                # segurança extra: write-phase tem de ser DEPOIS do node atual
                if wp_stage <= stage:
                    wp_stage = self._wp_next_free(pid, stage + 1, g.graph_id, blocked=blocked)

                # reservar e inserir
                self._wp_reserve(pid, wp_stage, g.graph_id)
                self._insert_write_phase_between(g, node, pid, wp_stage)
                self._mark_occupied(pid, wp_stage)  # write-phase também ocupa o stage globalmente

                inserted_wp += 1
                logger.debug(f"[Planner][Insert] write-phase at stage {wp_stage} (last_dirty_stage={last_dirty_stage})")

                # limpar variáveis “flushadas”
                for v in dirty_reads:
                    pending_writes.pop(v, None)

            # 2) registar novas escritas
            for v in writes:
                pending_writes[v] = stage

            logger.debug(f"[Planner][Check] node={node.id} ({node.instr.name}) stage={stage} reads={reads} writes={writes} pending={pending_writes}")

        logger.debug(f"[Planner][Summary] total write-phases inserted: {inserted_wp}")






    # ==========================================================
    #  NEEDS WRITE-PHASE CHECK
    # ==========================================================

    def _needs_write_phase(self, ordered_nodes: List[MicroGraph], node: MicroNode) -> bool:
        """
        Determines whether a write-phase is required after this node.
        Simple heuristic: if this node writes variables that are read by later nodes
        (in topological order).
        """
        if not node.effect or not node.effect.writes:
            return False

        found = False
        for n in ordered_nodes:
            if n.id == node.id:
                found = True
                continue
            if not found:
                continue
            if not n.effect:
                continue
            # dependency: later node reads something this node wrote
            if n.effect.reads & node.effect.writes:
                if __debug__:
                    logger.debug(f"[Planner][Dep] write-phase needed: {node.instr.name} -> {n.instr.name}")
                return True

        return False


    # ==========================================================
    #  INSERT WRITE-PHASE NODE
    # ==========================================================

    def _insert_write_phase_between(self, g: MicroGraph, node: MicroNode, pid: int, wp_stage: int) -> None:
        """
        Inserts a write-phase node *after* the given node.
        The node represents a pipeline stall where memory writes are flushed.
        """
        wp_id = self._new_internal_id(g.graph_id)
        wp_instr = MicroInstruction(
            name="write_phase_t",
            kwargs={"program_id": pid, "stage": wp_stage}
        )

        wp_node = MicroNode(
            id=wp_id,
            instr=wp_instr,
            graph_id=g.graph_id,
            allocated_stage=wp_stage,
            allocated_table="write_phase_t",
            flow_id=node.flow_id,
            effect=MicroEffect(),
        )

        g.nodes[wp_id] = wp_node

        # redirect edges (node → wp → next)
        new_edges = []
        for e in g.edges:
            if e.src == node.id:
                new_edges.append(MicroEdge(src=wp_id, dst=e.dst, dep=e.dep))
                e.dst = wp_id
        g.edges.extend(new_edges)

        if __debug__:
            logger.debug(f"[Planner][Graph] write-phase {wp_id} inserted after {node.id}")


    # ==========================================================
    #  WRITE-PHASE RESERVATION LOGIC
    # ==========================================================

    def _wp_reserve(self, pid: int, stage_idx: int, graph_id: str | None = None) -> None:
        """Mark this stage as having a write-phase for the given program and graph."""
        key = (pid, graph_id)
        self._wp_reserved.setdefault(key, set()).add(stage_idx)

        if __debug__:
            logger.debug(f"[Planner][WP] reserved stage {stage_idx} for pid={pid}, graph={graph_id}")


    def _wp_next_free(self, pid: int, start_stage: int, graph_id: str | None = None, blocked: set[int] | None = None) -> int:
        """
        Procura o próximo stage livre para write-phase, tendo em conta:
        - reservas anteriores de write-phase (globais por pid e opcionalmente por grafo)
        - stages já ocupados por instruções do mesmo programa (blocked)
        """

        # 1. Stage 1 is forbidden for write phase
        stage = max(start_stage, 2)

        key = (pid, graph_id)
        reserved = self._wp_reserved.get(key, set())
        occupied = self._occupied_for_pid(pid)
        blocked_all = set(blocked or set()) | reserved | occupied

        if __debug__:
            logger.debug(f"_wp_next_free start_stage:{start_stage} gid:{graph_id}")
            logger.debug(reserved)
            logger.debug(occupied)

        s = stage
        while s in blocked_all:
            s += 1
        return s
    
    def _is_stage_free(self, pid, current_stage, graph_id = None):
        key = (pid, graph_id)
        reserved = [i for s in self._wp_reserved.values() for i in s]
        occupied = [i for s in self._occupied_stages.values() for i in s]
        return (current_stage not in reserved) and (current_stage not in occupied)

    def _mark_occupied(self, pid: int, stage_idx: int) -> None:
        """Marca um stage como ocupado por alguma instrução deste programa (global por pid)."""
        if stage_idx is None:
            return
        self._occupied_stages.setdefault(pid, set()).add(stage_idx)

    def _occupied_for_pid(self, pid: int) -> set[int]:
        """Conjunto dos stages já ocupados globalmente (qualquer grafo) para este programa."""
        return self._occupied_stages.get(pid, set())
