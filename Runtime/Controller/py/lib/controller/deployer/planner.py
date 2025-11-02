from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from lib.tofino.constants import *

logger = logging.getLogger(__name__)

# importa os teus tipos reais
from .types import (
    MicroGraph,
    MicroNode,
    MicroEdge,
    MicroInstruction
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


            self._allocate_stages(g, pid, base_flow_id)
            planned_graphs.append(g)

        return PlanningResult(planned_graphs)
    # ============================================================
    # CORE
    # ============================================================

    def _allocate_stages(self, g: MicroGraph, pid: int, base_flow_id: int) -> None:
        order = self._topo_sort(g)
        current_stage = 1  # ISA começa em s1  :contentReference[oaicite:5]{index=5}

        for node in order:
            # a) IF: atribuir slot_map e gerar flows por ramo (propagação)
            if self._is_decide(node):
                self._assign_conditional_slots(node)   # preenche kwargs["slot_map"] (greedy v1..v4)
                self._assign_branch_flow_ids(g, node)  # cria novos flow_ids e propaga

            # b) escolher nome(s) candidatos (instr/alternative, ou speculative_*)
            cand_names = self._candidate_ops_for_node(node)

            # c) procurar à frente
            fwd = self._find_forward(cand_names, current_stage)
            if fwd is None:
                # d) tentar atrás e inserir recirculação
                back = self._find_backward(cand_names, start_before=current_stage)
                if back is None:
                    raise PlannerError(f"Instr '{node.instr.name}' (alt='{getattr(node.instr,'alternative', None)}') not supported by ISA.")
                # recircula antes deste node e propaga novo flow_id
                new_flow = self._insert_recirc_before(g, node, pid)
                self._propagate_flow_id(g, start_node_id=node.id, new_flow_id=new_flow)
                s_idx, flow, table, used_name = back
            else:
                s_idx, flow, table, used_name = fwd

            # e) selar alocação
            node.allocated_stage = s_idx
            node.allocated_table = f"{flow}.{table}"  # ex.: "f1.instructions_p2"
            node.allocated_flow  = flow               # f1/f2 (útil p/ installer)
            if used_name.lower() != node.instr.name.lower():
                node.instr.kwargs["_used_alternative"] = used_name
                node.instr.used_alternative = True

            # f) avançar ponteiro de stage
            current_stage = max(current_stage, s_idx + 1)

            # g) write-phase se necessário — e **realocar** após inserção
            dependents = [g.nodes[e.dst] for e in g.edges if e.dep == "DATA" and e.src == node.id]
            for nxt in dependents:
                logger.debug("[!] Dependents detected")
                if self._needs_write_phase(node, nxt):
                    wp_node = self._insert_write_phase_between(g, node.id, nxt.id)
                    # replanear a partir do write-phase (respeitando ISA)
                    self._reallocate_from(g, start_node=wp_node, start_stage=s_idx + 1)
                    current_stage = max(current_stage, (wp_node.allocated_stage or s_idx) + 1)

    # ============================================================
    # HELPERS: ISA pick / topo / recirc / write-phase / decide
    # ============================================================

    # === ISA helpers (v1.9) ======================================

    def _iter_stage_defs(self) -> List[Tuple[int, str, str, List[str]]]:
        """
        Yield (stage_index, flow_name, table_name, instr_list)
        for all (s1..s10) x (f1,f2) x (tables).
        Tables present per stage/flow depend on the JSON keys.  :contentReference[oaicite:2]{index=2}
        """
        pipe = self.isa.get("pipeline", {})
        out = []
        for s_idx in range(1, 11):
            s_key = f"s{s_idx}"
            s = pipe.get(s_key, {})
            for flow in ("f1", "f2"):
                f = s.get(flow, {})
                # s10: 'multi_instr_speculative'; s1: 'instructions_p1'; s2..s9: 'instructions_p2' + 'instructions_speculative'
                # for table in ("instructions_p1", "instructions_p2", "instructions_speculative", "multi_instr_speculative"):
                for table in f:
                    instrs = f[table]
                    out.append((s_idx, flow, table, [x.lower() for x in instrs]))
        return out

    def _find_forward(self, names: List[str], start_stage: int) -> Optional[Tuple[int,str,str,str]]:
        """
        Search forward from start_stage for any of 'names'.
        Returns (stage_index, flow, table_name, used_name) or None.
        """
        names = [n.lower() for n in names if n]
        for (s_idx, flow, table, instrs) in self._iter_stage_defs():
            if s_idx < max(1, start_stage):  # stages start at 1
                continue
            for nm in names:
                if nm in instrs:
                    return (s_idx, flow, table, nm)
        return None

    def _find_backward(self, names: List[str], start_before: int) -> Optional[Tuple[int,str,str,str]]:
        """
        Search backward from start_before-1 down to s1.
        Returns (stage_index, flow, table_name, used_name) or None.
        """
        names = [n.lower() for n in names if n]
        for (s_idx, flow, table, instrs) in sorted(self._iter_stage_defs(), key=lambda x: -x[0]):
            if s_idx >= start_before:
                continue
            for nm in names:
                if nm in instrs:
                    return (s_idx, flow, table, nm)
        return None

    def _reallocate_from(self, g: MicroGraph, start_node: MicroNode, start_stage: int) -> None:
        """
        Re-allocate stages from 'start_node' forward (DATA order) using ISA rules again.
        """
        order = self._topo_sort(g)
        started = False
        current_stage = start_stage

        for node in order:
            if not started:
                if node.id == start_node.id:
                    started = True
                else:
                    continue

            # write-phase node: força “tabela” simbólica
            if str(getattr(node.instr, "name", "")).lower() == "write_phase":
                node.allocated_stage = current_stage
                node.allocated_table = "write_phase"
                node.allocated_flow  = getattr(node, "allocated_flow", "f1")
                current_stage += 1
                continue

            cand_names = self._candidate_ops_for_node(node)
            fwd = self._find_forward(cand_names, current_stage)
            if fwd is None:
                # tentar uma recirculação local (pouco comum neste ponto)
                back = self._find_backward(cand_names, start_before=current_stage)
                if back is None:
                    raise PlannerError(f"Reallocation failed for node {node.id} ({node.instr.name}).")
                s_idx, flow, table, used_name = back
            else:
                s_idx, flow, table, used_name = fwd

            node.allocated_stage = s_idx
            node.allocated_table = f"{flow}.{table}"
            node.allocated_flow  = flow
            current_stage = max(current_stage, s_idx + 1)



    def _is_decide(self, node) -> bool:
        return str(getattr(node.instr, "name", "")).lower() == "decide"

    def _isa_pick_table(self, node, start_from_stage: int):
        """
        Procura em stages >= start_from_stage uma tabela que suporte
        node.instr.name; se não houver, tenta .alternative.
        Retorna (stage, table_name, used_instr_name) ou None.
        """
        name = node.instr.name.lower()
        alt  = (getattr(node.instr, "alternative", None) or "").lower()

        stages = self.isa.get("pipeline", {}).get("stages", [])
        for s in range(max(0, start_from_stage), len(stages)):
            for t in stages[s].get("tables", []):
                instrs = [i.lower() for i in t.get("instrs", [])]
                if name in instrs:
                    return s, t["name"], node.instr.name
                if alt and alt in instrs:
                    return s, t["name"], getattr(node.instr, "alternative")
        return None

    def _isa_pick_table_backward(self, node, start_from: int):
        """
        Procura “para trás” (stage decrescentes) — usado antes de recirculação.
        Retorna (stage, table_name, used_instr_name) ou None.
        """
        name = node.instr.name.lower()
        alt  = (getattr(node.instr, "alternative", None) or "").lower()

        stages = self.isa.get("pipeline", {}).get("stages", [])
        for s in range(start_from, -1, -1):
            for t in stages[s].get("tables", []):
                instrs = [i.lower() for i in t.get("instrs", [])]
                if name in instrs:
                    return s, t["name"], node.instr.name
                if alt and alt in instrs:
                    return s, t["name"], getattr(node.instr, "alternative")
        return None
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

    def _insert_recirc_before(self, g: MicroGraph, node, pid: int) -> int:
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
        rec_node = MicroNode(id=rec_id, instr=rec_instr, graph_id=g.graph_id)
        rec_node.flow_id = node.flow_id
        g.nodes[rec_id] = rec_node


        # redirect edges arriving to node
        for e in g.edges:
            if e.dst == node.id:
                e.dst = rec_id
                # update instr_id of the predecessor to point to new flow
                pred_node = g.nodes[e.src]
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


    def _propagate_flow_id(self, g, start_node_id: int, new_flow_id: int) -> None:
        """
        Propaga flow_id a partir de 'start_node_id' para todos os nós alcançáveis
        (por DATA e CONTROL), até que outro decide/recirc altere novamente.
        """
        seen = set()
        stack = [start_node_id]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            node = g.nodes.get(nid)
            if not node:
                continue
            node.flow_id = new_flow_id
            for e in g.edges:
                if e.src == nid:
                    stack.append(e.dst)

    def _needs_write_phase(self, src_node, dst_node) -> bool:
        """
        RAW entre src e dst? Se sim, requer write-phase:
          - src.effect.writes & dst.effect.reads != ∅
        """
        src_w = getattr(getattr(src_node, "effect", None), "writes", set()) or set()
        dst_r = getattr(getattr(dst_node, "effect", None), "reads", set()) or set()
        logger.debug(f"src_w={src_w} dst_r={dst_r}")
        logger.debug(f"result op bool(src_w & dst_r): {bool(src_w & dst_r)}")
        return bool(src_w & dst_r)

    def _insert_write_phase_between(self, g: MicroGraph, src_id: int, dst_id: int) -> MicroNode:
        """
        Insert a write-phase node between src and dst.
        """
        wp_id = self._new_internal_id()
        wp_instr = MicroInstruction(name="write_phase", kwargs={})
        wp_node = MicroNode(id=wp_id, instr=wp_instr, graph_id=g.graph_id)
        wp_node.flow_id = g.nodes[src_id].flow_id

        g.nodes[wp_id] = wp_node

        new_edges = []
        for e in g.edges:
            if e.dep == "DATA" and e.src == src_id and e.dst == dst_id:
                new_edges.append(MicroEdge(src=src_id, dst=wp_id, dep="DATA"))
                new_edges.append(MicroEdge(src=wp_id, dst=dst_id, dep="DATA"))
            else:
                new_edges.append(e)
        g.edges = new_edges

        return wp_node