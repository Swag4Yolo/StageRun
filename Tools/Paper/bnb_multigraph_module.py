
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
from copy import deepcopy

# ---------------- Common hardware model ----------------

@dataclass
class Table:
    name: str
    capabilities: Set[str]
    capacity: int

@dataclass
class Stage:
    index: int
    flows: Dict[int, List[Table]] = field(default_factory=dict)

def build_pipeline(num_stages: int = 4) -> List[Stage]:
    stages = []
    for s in range(num_stages):
        stage = Stage(index=s, flows={})
        for flow in (0,1):
            stage.flows[flow] = [
                Table(name=f"S{s}F{flow}A", capabilities={"ALU","REG_READ"}, capacity=3),
                Table(name=f"S{s}F{flow}B", capabilities={"REG_WRITE","WRITE_PHASE"}, capacity=2),
            ]
        stages.append(stage)
    return stages

# ---------------- Micro-graph structures ----------------

@dataclass
class MicroNode:
    id: str
    op: str                      # 'ALU','REG_READ','REG_WRITE','WRITE_PHASE'
    reads: Set[str] = field(default_factory=set)   # 'reg:NAME[key]' or 'hash:NAME[key]'
    writes: Set[str] = field(default_factory=set)
    requires: Set[str] = field(default_factory=set)
    preds: Set[str] = field(default_factory=set)   # predecessors within this graph
    succs: Set[str] = field(default_factory=set)

class MicroGraph:
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, MicroNode] = {}

    def add(self, n: MicroNode):
        self.nodes[n.id] = n

    def add_edge(self, u: str, v: str):
        self.nodes[u].succs.add(v)
        self.nodes[v].preds.add(u)

    def topo(self) -> List[str]:
        indeg = {nid: len(n.preds) for nid,n in self.nodes.items()}
        q = deque([nid for nid,c in indeg.items() if c==0])
        order = []
        while q:
            u = q.popleft()
            order.append(u)
            for v in self.nodes[u].succs:
                indeg[v] -= 1
                if indeg[v]==0:
                    q.append(v)
        if len(order)!=len(self.nodes):
            raise RuntimeError(f"Cycle in micro-graph {self.name}")
        return order

# ---------------- Placement state with resource co-location ----------------

@dataclass
class Placement:
    node_to_slot: Dict[Tuple[str,str], Tuple[int,int,str]] = field(default_factory=dict)   # (g,id) -> (stage, flow, table)
    table_usage: Dict[Tuple[int,int,str], int] = field(default_factory=lambda: defaultdict(int))
    recircs: int = 0
    stage_locked: Set[int] = field(default_factory=set)                         # stages locked by WP
    res_stage: Dict[str, int] = field(default_factory=dict)                     # resource ('reg:...','hash:...') -> stage index

def node_resources(n: MicroNode) -> Set[str]:
    return {r for r in n.reads.union(n.writes) if r.startswith("reg:") or r.startswith("hash:")}

def can_place(node: MicroNode, gname: str, stage: Stage, flow: int, table: Table, placement: Placement,
              preds_placed: bool, force_table_progress: bool = True) -> bool:
    """
    Check if a node can be placed in the given (stage, flow, table).
    - Enforces table order: successor must be placed in a later table than its predecessor if same stage.
    - Respects stage locks, resource co-location, and table capacities.
    """
    if not preds_placed:
        return False
    # 1) Stage locked by write-phase → only WRITE_PHASE allowed
    if stage.index in placement.stage_locked and node.op != "WRITE_PHASE":
        return False
    # 2) Table capability check
    if not node.requires.issubset(table.capabilities):
        return False
    # 3) Table capacity
    key = (stage.index, flow, table.name)
    if placement.table_usage[key] >= table.capacity:
        return False
    # 4) Resource co-location (regs/hashes)
    for res in node_resources(node):
        if res in placement.res_stage and placement.res_stage[res] != stage.index:
            return False
    # 5) NEW RULE: enforce intra-stage table order consistency
    if force_table_progress:
        for (g, pred_id), (p_stage, p_flow, p_table) in placement.node_to_slot.items():
            if g == gname and pred_id in node.preds and p_stage == stage.index and p_flow == flow:
                table_list = [t.name for t in stage.flows[flow]]
                # successor must be placed AFTER predecessor in the table list
                if table_list.index(table.name) <= table_list.index(p_table):
                    return False
    return True

def place(node: MicroNode, gname: str, stage: Stage, flow: int, table: Table, placement: Placement) -> Placement:
    newp = Placement(node_to_slot=dict(placement.node_to_slot),
                     table_usage=defaultdict(int, placement.table_usage),
                     recircs=placement.recircs,
                     stage_locked=set(placement.stage_locked),
                     res_stage=dict(placement.res_stage))
    key = (stage.index, flow, table.name)
    newp.node_to_slot[(gname, node.id)] = (stage.index, flow, table.name)
    newp.table_usage[key] += 1
    if node.op == "WRITE_PHASE":
        newp.stage_locked.add(stage.index)
    for res in node_resources(node):
        if res not in newp.res_stage:
            newp.res_stage[res] = stage.index
    return newp

def lower_bound_min_recirc_multigraph(graphs: Dict[str, MicroGraph]) -> int:
    counts = defaultdict(int)
    for g in graphs.values():
        for n in g.nodes.values():
            for r in n.reads.union(n.writes):
                if r.startswith("reg:") or r.startswith("hash:"):
                    counts[r] += 1
    lb = 0
    for c in counts.values():
        lb = max(lb, max(0, c-1))
    return lb

# Iterative BnB (non-recursive) to avoid recursion limits.
def bnb_place_multi(graphs: Dict[str, MicroGraph], stages: List[Stage],
                    budget:int=20000, stop_at_zero=True) -> Optional[Placement]:
    orders = {name: g.topo() for name,g in graphs.items()}
    op_weight = {"WRITE_PHASE": 0, "REG_WRITE": 1, "REG_READ": 2, "ALU": 3}

    init_idx = {name: 0 for name in graphs}
    stack = [(Placement(), init_idx, None, budget)]
    best = None
    best_ub = float("inf")

    while stack:
        placement, idx, choices, bud = stack.pop()
        if bud <= 0:
            continue

        lb = lower_bound_min_recirc_multigraph(graphs)
        if lb >= best_ub:
            continue

        if all(idx[name] == len(orders[name]) for name in graphs):
            if placement.recircs < best_ub:
                best, best_ub = placement, placement.recircs
            if stop_at_zero and placement.recircs == 0:
                break
            continue

        if choices is None:
            frontier = []
            for gname in graphs:
                if idx[gname] < len(orders[gname]):
                    nid = orders[gname][idx[gname]]
                    ok = True
                    for p in graphs[gname].nodes[nid].preds:
                        if (gname, p) not in placement.node_to_slot:
                            ok = False; break
                    if ok:
                        frontier.append((gname, nid))
            frontier.sort(
                key=lambda gn: op_weight.get(graphs[gn[0]].nodes[gn[1]].op, 10)
            )
            choices = frontier

        progressed_any = False
        for (gname, nid) in choices:
            node = graphs[gname].nodes[nid]
            feasible_slots = []
            for st in stages:
                for flow, tables in st.flows.items():
                    for tab in tables:
                        if can_place(node, gname, st, flow, tab, placement, True):
                            feasible_slots.append((st,flow,tab))
            for (st,flow,tab) in feasible_slots:
                progressed_any = True
                new_place = place(node, gname, st, flow, tab, placement)
                new_idx = dict(idx); new_idx[gname] += 1
                stack.append((new_place, new_idx, None, bud-1))

        if not progressed_any and (best is None or placement.recircs + 1 < best_ub):
            newp = Placement(node_to_slot=dict(placement.node_to_slot),
                             table_usage=defaultdict(int, placement.table_usage),
                             recircs=placement.recircs + 1,
                             stage_locked=set(placement.stage_locked),
                             res_stage=dict(placement.res_stage))
            stack.append((newp, dict(idx), None, bud-1))

    return best
