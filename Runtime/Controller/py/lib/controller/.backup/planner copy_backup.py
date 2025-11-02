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
    stats: PlannerStats

class PlannerError(Exception):
    pass

# ============================
#        PLANNER
# ============================

class Planner:
    """
    Planeia MicroGraphs:
      1) resolve ChoiceGroups
      2) ordena nós (topo sort)
      3) aloca stages (simplificado; depois afinamos com ISA)
      4) injeta program_id em todas as micro-instruções
      5) atribui flow_id por grafo e por ramos (IF), e propaga next_flow_id
      6) distribui writes em flows + (gancho) para write phases

    Interface:
      plan(micro_graphs, isa, pid) -> PlanningResult
    """

    def __init__(self, isa: Dict[str, Any]):
        self.isa = isa
        self.stats = PlannerStats()
        self._flow_counter = 0  # <--- global por plan() / programa

    def _new_flow_id(self) -> int:
        self._flow_counter += 1
        return self._flow_counter
    
    # ----------------------------
    # Público
    # ----------------------------
    def plan(self, micro_graphs: List[MicroGraph], pid: int) -> PlanningResult:
        planned: List[MicroGraph] = []
        
        # self._flow_counter = 0


        for g in micro_graphs:
            # 1. Add PreFilter Keys
            g.keys['kwargs']['program_id'] = pid

            order = self._topo_sort(g)
            self._allocate_stages(g, order)
            self._inject_program_id(g, pid)
            base_flow = self._new_flow_id()
            self._assign_flow_ids_and_propagate_next(g, order, pid, base_flow)
            self._compile_decide(g, order)
            self._assign_flows_and_write_phases(g, order)
            planned.append(g)

        # stats
        self.stats.total_nodes = sum(len(g.nodes) for g in planned)
        self.stats.stages_used = (
            max((n.allocated_stage or 0) for g in planned for n in g.nodes.values()) + 1
            if planned and planned[0].nodes else 0
        )
        self.stats.total_flows = 2

        return PlanningResult(graphs=planned, stats=self.stats)
    
    def _compile_decide(self, g, order):
        """
        Converte cada nó 'decide' num speculative_conditional_* físico.
        Mapeamento de variáveis é local ao prefilter (grafo).
        """
        control_out = {e.src: [] for e in g.edges if e.dep == "CONTROL"}
        for e in g.edges:
            if e.dep == "CONTROL":
                control_out[e.src].append((e.label or "", e.dst))

        # mapeamento *local* de variáveis -> slots (reset por grafo)
        var_to_slot: dict[str, str] = {}
        available = ["v1", "v2", "v3", "v4"]

        def assign_slot(var: str) -> str:
            if var in var_to_slot:
                return var_to_slot[var]
            if not available:
                raise RuntimeError(f"Prefilter '{g.graph_id}': esgotados os slots físicos (v1..v4)")
            slot = available.pop(0)
            var_to_slot[var] = slot
            return slot

        for node in order:
            if getattr(node.instr, "instr", "") != "decide":
                continue

            cond_ir = node.instr.kwargs.get("cond_ir", {})
            branches = cond_ir.get("branches", [])
            if not branches:
                continue

            # usa o primeiro branch para deduzir os termos (DNF simplificada)
            first = branches[0]
            terms = (first.get("dnf", [[]])[0])[:2]  # até 2 comparações

            # analisar termos
            term_slots = []
            constants = []
            for t in terms:
                left = t.get("var")
                const = t.get("const")
                if isinstance(const, (int, float)):
                    # var == CONST
                    slot = assign_slot(left)
                    term_slots.append(slot)
                    constants.append(const)
                elif isinstance(const, str):
                    # var == outra_var
                    slot1 = assign_slot(left)
                    slot2 = assign_slot(const)
                    term_slots.extend([slot1, slot2])
                    constants = []  # comparação direta, sem constantes
                else:
                    continue

            # determinar micro-instrucao
            if len(constants) == 2:
                node.instr.instr = f"speculative_conditional_{term_slots[0]}_{term_slots[1]}"
                node.instr.kwargs["cond_mode"] = t.get("op", "EQ")
                node.instr.kwargs["cond_val"] = constants[0]
                node.instr.kwargs["cond_mode_2"] = t.get("op", "EQ")
                node.instr.kwargs["cond_val_2"] = constants[1]
            elif not constants and len(term_slots) >= 2:
                node.instr.instr = "speculative_conditional_between_vars"
                node.instr.kwargs["cond_mode"] = "EQ"
                node.instr.kwargs["cond_val"] = 0
                node.instr.kwargs["cond_mode_2"] = "EQ"
                node.instr.kwargs["cond_val_2"] = 0
            else:
                node.instr.instr = "speculative_conditional_v1_v2"  # fallback

            node.instr.kwargs["slot_map"] = dict(var_to_slot)
            node.selected_op = node.instr.instr

            # ligar ramos (branch_targets)
            if not node.instr.kwargs.get("branch_targets"):
                node.instr.kwargs["branch_targets"] = [
                    {"label": lbl, "dst": dst, "flow_id": getattr(g.nodes.get(dst), "flow_id", None)}
                    for (lbl, dst) in control_out.get(node.id, [])
                ]

        # atualizar contexto global
        g.var_slot_map = var_to_slot
        g.available_slots = available

    # ----------------------------
    # 2) Topological sort
    # ----------------------------
    def _topo_sort(self, g: MicroGraph) -> list:
        """
        Compute a topological order of nodes in a MicroGraph.

        Each node appears *after* all the nodes it depends on.
        If the graph has cycles, remaining nodes are appended at the end.
        """

        # Step 1: Initialize helper structures
        indegree = {}   # how many incoming edges each node has
        successors = {} # adjacency list (who depends on this node)

        for node_id in g.nodes:
            indegree[node_id] = 0
            successors[node_id] = []

        # Step 2: Build the adjacency list and indegree counts
        for edge in g.edges:
            src, dst = edge.src, edge.dst
            if src not in g.nodes or dst not in g.nodes:
                continue  # ignore broken edges

            successors[src].append(dst)  # src → dst
            indegree[dst] += 1           # dst has one more dependency

        if __debug__:
            print("\n[TopoSort] Initial indegree per node:")
            for nid, deg in indegree.items():
                print(f"  Node {nid}: indegree = {deg}")

        # Step 3: Start with nodes that have no dependencies (indegree == 0)
        ready_nodes = [nid for nid, deg in indegree.items() if deg == 0]
        topo_order = []

        if __debug__:
            print(f"[TopoSort] Starting with ready nodes: {ready_nodes}")

        # Step 4: Process nodes one by one
        while ready_nodes:
            # Take one node with no remaining dependencies
            current_id = ready_nodes.pop(0)
            current_node = g.nodes[current_id]
            topo_order.append(current_node)

            if __debug__:
                print(f"[TopoSort] Visiting node {current_id}")

            # For every node that depends on this one
            for neighbor_id in successors[current_id]:
                indegree[neighbor_id] -= 1  # one dependency satisfied
                if indegree[neighbor_id] == 0:
                    # Now ready to process
                    ready_nodes.append(neighbor_id)

        # Step 5: Handle cycles (if any)
        if len(topo_order) < len(g.nodes):
            logger.warning("[TopoSort] WARNING: graph has cycles, adding remaining nodes.")
            already_seen = {n.id for n in topo_order}
            for node_id, node in g.nodes.items():
                if node_id not in already_seen:
                    topo_order.append(node)

        # Step 6: Done
        if __debug__:
            logger.debug("\n[TopoSort] Final order of node IDs:", [n.id for n in topo_order])

        return topo_order

    # ---------------- Planner helpers (NEW) ----------------

    def _recirc_spec(self):
        """Lê do ISA a configuração de recirculação, com fallbacks razoáveis."""
        rec = self.isa.get("recirculation", {})
        return {
            "op": rec.get("op", "pos_filter_recirc_same_pipe"),
            "stage": int(rec.get("stage", self.isa.get("max_stages", 10))),
            "flow": int(rec.get("flow", 1)),
            "table": rec.get("table", self._isa_pick_table(rec.get("op", "pos_filter_recirc_same_pipe"),
                                                        int(rec.get("stage", self.isa.get("max_stages", 10))),
                                                        int(rec.get("flow", 1))))
        }

    def _find_anywhere_supported(self, op: str) -> tuple[int,int,str] | None:
        """Procura um (stage, flow, table) em TODO o pipeline onde 'op' exista."""
        max_stage = int(self.isa.get("max_stages", 10))
        for s in range(1, max_stage + 1):
            for f in (1, 2):
                table = self._isa_pick_table(op, s, f)
                if table:
                    return (s, f, table)
        return None

    def _insert_recirc_before(self, g, anchor_node, pid: int, target_s: int, target_f: int) -> int:
        """
        Insere um nó de recirculação (`pos_filter_recirc_same_pipe`) imediatamente antes de `anchor_node`.

        - Cria um novo flow_id (para o novo passe do programa)
        - Substitui as edges que iam diretamente para `anchor_node` por novas edges:
            preds -> recirc_node (dep="RECIRC")
            recirc_node -> anchor_node (dep="DATA")
        - Configura os kwargs da instrução de recirculação (f1_next_instr, f2_next_instr, program_id)
        - Propaga o novo flow_id a todos os nós seguintes (excepto IFs ou outras recircs)
        """

        # 1. Especificação base de recirculação (ISA-aware)
        rec = self._recirc_spec()
        new_flow = self._new_flow_id()

        # 2. Criação robusta de edges (permite grafos vazios)
        EdgeCls = None
        if hasattr(g, "edges") and len(g.edges) > 0:
            EdgeCls = type(g.edges[0])
        else:
            # fallback para SimpleNamespace
            from types import SimpleNamespace
            EdgeCls = SimpleNamespace

        def make_edge(src, dst, dep="DATA", label=None):
            return EdgeCls(src=src, dst=dst, dep=dep)

        # 3. Criar o novo nó de recirculação
        rec_id = max(g.nodes.keys(), default=0) + 1
        from types import SimpleNamespace

        rec_instr = SimpleNamespace(instr=rec["op"], kwargs={
            "f1_next_instr": ["DISABLED", "DISABLED"],
            "f2_next_instr": ["DISABLED", "DISABLED"],
            "program_id": [pid, MASK_PROGRAM_ID],
        })

        rec_node = SimpleNamespace(
            id=rec_id,
            instr=rec_instr,
            allocated_stage=rec["stage"],
            allocated_flow=rec["flow"],
            allocated_table=rec["table"],
            selected_op=rec["op"],
            flow_id=getattr(anchor_node, "flow_id", None),  # ainda é o flow atual
            graph_id=g.graph_id,
        )

        g.nodes[rec_id] = rec_node

        # 4. Reestruturar as edges: preds -> recirc -> anchor
        preds = [e.src for e in g.edges if e.dst == anchor_node.id]

        # remover edges antigas (pred -> anchor)
        g.edges = [e for e in g.edges if not (e.dst == anchor_node.id and e.src in preds)]

        # criar edges preds -> recirc (tipo "RECIRC" para o Installer identificar)
        for p in preds:
            g.edges.append(make_edge(p, rec_id, dep="RECIRC"))

        # criar edge recirc -> anchor (continuação normal)
        g.edges.append(make_edge(rec_id, anchor_node.id, dep="DATA"))

        # 5. Configurar o nó de recirculação com o próximo flow_id
        if target_f == 1:
            rec_node.instr.kwargs["f1_next_instr"] = ["DISABLED", new_flow]
        else:
            rec_node.instr.kwargs["f2_next_instr"] = ["DISABLED", new_flow]

        # o anchor_node passa a pertencer ao novo flow
        anchor_node.flow_id = new_flow

        # 6. Propagar o novo flow_id aos nós subsequentes (DATA edges apenas)
        visited = set()
        stack = [anchor_node.id]
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)

            node = g.nodes.get(nid)
            if node is None:
                continue

            instr_name = getattr(node.instr, "instr", "")
            # não propagar para IFs nem recircs
            if instr_name.startswith("speculative_conditional") or instr_name.startswith("conditional"):
                continue
            if instr_name.startswith("pos_filter_recirc"):
                continue

            # atualizar o flow_id
            node.flow_id = new_flow

            # seguir apenas DATA edges (as RECIRC indicam saltos físicos)
            succs = [e.dst for e in g.edges if e.src == nid and e.dep == "DATA"]
            stack.extend(succs)

        # 7. Log opcional para debug
        if getattr(self, "_verbose", False):
            print(f"[Planner] Inserted recirculation node {rec_id} before node {anchor_node.id}, new_flow={new_flow}")

        return new_flow


    # ----------------------------
    # 3) Stage allocation (simple)
    # ----------------------------

    def _isa_pick_table(self, micro_instr_name: str, stage: int, flow: int) -> str | None:
        """
        Se o op existir no s{stage}/f{flow}, devolve o nome da tabela.
        - Se a entrada for string, aceita: devolve None (ou um default do ISA, se tiveres).
        - Se a entrada for dict, usa o campo 'table'.
        """
        pipeline = self.isa.get("pipeline", {})
        s_key, f_key = f"s{stage}", f"f{flow}"
        tables = pipeline[s_key][f_key]
        logger.debug(tables)
        logger.debug(micro_instr_name)
        logger.debug(stage)
        logger.debug(flow)

        for table_name in tables:
            if micro_instr_name in tables[table_name]:
                return table_name
        return None

    def _allocate_stages(self, g:MicroGraph, sorted_nodes:List[MicroNode]):
        """
        ISA-aware + Decide + Recirculação:
        1) respeita deps (min_stage = max(pred)+1)
        2) tenta colocar no [min_stage..max] em flows {1,2}
        3) se ainda falhar mas existir suporte em estágios anteriores,
            insere recirculação (novo flow_id) e coloca no novo passe
        """
        preds: dict[int, list[int]] = {}
        for e in g.edges:
            preds.setdefault(e.dst, []).append(e.src)

        max_stage = int(self.isa.get("max_stages", 10))
        cap = int(self.isa.get("stage_capacity_per_flow", 8))
        used: dict[tuple[int,int], int] = {}


        def fits(s,f): return used.get((s,f),0) < cap

        for node in sorted_nodes:
            op = node.instr.name
            min_stage = 1
            for p in preds.get(node.id, []):
                st = getattr(g.nodes[p], "allocated_stage", None)
                if st is not None:
                    min_stage = max(min_stage, st + 1)

            # ---- tratamento especial para IF (decide): tenta normal e speculative
            if op == "decide":
                candidate_ops = [
                    "conditional_v1_v2", "conditional_v3_v4", "conditional_between_vars",
                    "speculative_conditional_v1_v2", "speculative_conditional_v3_v4",
                    "speculative_conditional_between_vars",
                ]
                placed = False
                # 1) tentar dentro do passe atual (s >= min_stage)
                for s in range(min_stage, max_stage + 1):
                    for f in (1, 2):
                        for cand in candidate_ops:
                            table = self._isa_pick_table(cand, s, f)
                            if table and fits(s, f):
                                node.allocated_stage = s
                                node.allocated_flow  = f
                                node.allocated_table = table
                                node.selected_op     = cand
                                used[(s,f)] = used.get((s,f),0)+1
                                placed = True
                                break
                        if placed: break
                    if placed: break

                # 2) se não coube no pass atual, tenta “atrás” (estágios anteriores)
                if not placed:
                    back = None
                    for s in range(1, min_stage):
                        for f in (1, 2):
                            for cand in candidate_ops:
                                table = self._isa_pick_table(cand, s, f)
                                if table:
                                    back = (s, f, table, cand)
                                    break
                            if back: break
                        if back: break

                    if back:
                        s_back, f_back, tbl_back, cand = back
                        # inserir recirculação, criar novo flow_id e atribuir nó ao novo passe
                        new_flow = self._insert_recirc_before(g, node, getattr(self, "_current_pid", 0), s_back, f_back)
                        node.allocated_stage = s_back
                        node.allocated_flow  = f_back
                        node.allocated_table = tbl_back
                        node.selected_op     = cand
                        node.flow_id         = new_flow
                        used[(s_back,f_back)] = used.get((s_back,f_back),0)+1
                        placed = True

                if not placed:
                    raise PlannerError(f"Prefilter '{g.graph_id}': IF node (decide) could not be placed (no conditional instr. in ISA)")

                continue  # próximo nó

            # ---- nós “normais” ----

            # 1) tentar no passe atual
            placed = False
            for s in range(min_stage, max_stage + 1):
                for f in (1, 2):
                    table = self._isa_pick_table(node.instr.name, s, f)
                    if table and fits(s, f):
                        node.allocated_stage = s
                        node.allocated_flow  = f
                        node.allocated_table = table
                        node.selected_op     = cand
                        used[(s,f)] = used.get((s,f),0)+1
                        placed = True
                        break
                    else:
                        table = self._isa_pick_table(node.instr.alternative, s, f)
                        if table and fits(s, f):
                            node.allocated_stage = s
                            node.allocated_flow  = f
                            node.allocated_table = table
                            node.selected_op     = cand
                            used[(s,f)] = used.get((s,f),0)+1
                            placed = True
                            node.instr.used_alternative = True
                            break
                    if placed: break
                if placed: break

            # 2) se não coube no passe atual, tenta “atrás” e recircula
            if not placed:
                back = None
                for s in range(1, min_stage):
                    for f in (1, 2):
                        for cand in alt_ops:
                            table = self._isa_pick_table(cand, s, f)
                            if table:
                                back = (s, f, table, cand)
                                break
                        if back: break
                    if back: break

                if back:
                    s_back, f_back, tbl_back, cand = back
                    new_flow = self._insert_recirc_before(g, node, getattr(self, "_current_pid", 0), s_back, f_back)
                    node.allocated_stage = s_back
                    node.allocated_flow  = f_back
                    node.allocated_table = tbl_back
                    node.selected_op     = cand
                    node.flow_id         = new_flow
                    used[(s_back,f_back)] = used.get((s_back,f_back),0)+1
                    placed = True

            if not placed:
                raise PlannerError(f"Instruction '{op}' has not been placed in any stage/flow (and no recirculation option found)")


    # ----------------------------
    # 4) Injetar program_id
    # ----------------------------
    def _inject_program_id(self, g: MicroGraph, pid: int) -> None:
        for n in g.nodes.values():
            # garante kwargs
            if not hasattr(n.instr, "kwargs") or n.instr.kwargs is None:
                n.instr.kwargs = {}
            n.instr.kwargs.setdefault("program_id", pid)

    # ----------------------------
    # 5) Flow IDs + next_flow_id
    # ----------------------------
    def _assign_flow_ids_and_propagate_next(self, g: MicroGraph, order: List[MicroNode], pid: int, base_flow: int) -> None:
        """
        Regra:
          - Cada grafo começa com flow_id = 1 
          - Em cada 'decide' (IF), atribuímos novos flow_ids para a entrada de cada ramo.
          - O nó imediatamente anterior ao início de um ramo deve ter kwargs['next_flow_id'] = flow_id_do_ramo.
            No teu caso, é o próprio 'decide' que conhece os ramos, por isso colocamos:
               decide.kwargs['branch_flow_ids'] = { label: flow_id_branch }
          - Nós sem bifurcação herdam o flow_id do predecessor.
        """
        # Índices rápidos
        preds: Dict[int, List[int]] = {}
        succs: Dict[int, List[int]] = {}
        control_out: Dict[int, List[Tuple[str, int]]] = {}  # decide_id -> [(label, dst_id), ...]

        for e in g.edges:
            succs.setdefault(e.src, []).append(e.dst)
            preds.setdefault(e.dst, []).append(e.src)
            if e.dep == "CONTROL":
                control_out.setdefault(e.src, []).append((e.label or "", e.dst))

        node_flow: Dict[int,int] = {}

        # roots do grafo começam com base_flow (único por prefilter)
        roots = [n.id for n in order if len(preds.get(n.id, [])) == 0]
        for rid in roots:
            node_flow[rid] = base_flow

        for node in order:
            nid = node.id
            if nid not in node_flow:
                for p in preds.get(nid, []):
                    if p in node_flow:
                        node_flow[nid] = node_flow[p]
                        break

            if node.instr.name == "decide":
                branch_map = {}
                for label, dst in control_out.get(nid, []):
                    branch_flow = self._new_flow_id()
                    branch_map[label or f"br-{dst}"] = branch_flow
                    node_flow[dst] = branch_flow
                node.instr.kwargs.setdefault("branch_flow_ids", branch_map)
                node.instr.kwargs.setdefault("branch_targets", [
                    {"label": lbl, "dst": dst, "flow_id": branch_map.get(lbl)}
                    for (lbl, dst) in control_out.get(nid, [])
                ])

        # guardar flow_id e next_flow_id default (linear = o próprio flow)
        for n in g.nodes.values():
            fid = node_flow.get(n.id)
            if fid is not None:
                n.flow_id = fid
            n.instr.kwargs.setdefault("next_flow_id", n.flow_id)


    # ----------------------------
    # 6) Flows + write phase (simplificado)
    # ----------------------------
    def _assign_flows_and_write_phases(self, g: MicroGraph, order: List[MicroNode]) -> None:
        """
        Mínimo viável: se a instrução é write, alterna flow 1/2 para permitir paralelismo.
        (A inserção de write_phase real pode ser feita aqui quando definires o mecanismo.)
        """
        current_flow_lane = 1
        for n in order:
            if self._is_write(n):
                n.allocated_flow = current_flow_lane
                current_flow_lane = 2 if current_flow_lane == 1 else 1
            else:
                # por omissão, corre no flow 1 (ou poderias herdar do predecessor)
                n.allocated_flow = n.allocated_flow or 1


    # ----------------------------
    # Helpers
    # ----------------------------
    def _is_write(self, node: MicroNode) -> bool:
        op = node.instr.name
        return op.startswith("hdr_write") or op.startswith("var_write")
