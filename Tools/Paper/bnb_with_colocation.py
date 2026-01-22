
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path

@dataclass
class Table:
    name: str
    capabilities: Set[str]
    capacity: int

@dataclass
class Stage:
    index: int
    flows: Dict[int, List[Table]] = field(default_factory=dict)

def build_pipeline(num_stages: int = 3) -> List[Stage]:
    stages = []
    for s in range(num_stages):
        stage = Stage(index=s, flows={})
        for flow in (0,1):
            stage.flows[flow] = [
                Table(name=f"S{s}F{flow}A", capabilities={"ALU","REG_READ"}, capacity=4),
                Table(name=f"S{s}F{flow}B", capabilities={"REG_WRITE","WRITE_PHASE"}, capacity=2),
            ]
        stages.append(stage)
    return stages

@dataclass
class MicroNode:
    id: str
    op: str
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    requires: Set[str] = field(default_factory=set)
    preds: Set[str] = field(default_factory=set)
    succs: Set[str] = field(default_factory=set)
    program: Optional[str] = None

class MicroGraph:
    def __init__(self):
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
            raise RuntimeError("Cycle in micro-graph")
        return order

@dataclass
class Placement:
    node_to_slot: Dict[str, Tuple[int,int,str]] = field(default_factory=dict)
    table_usage: Dict[Tuple[int,int,str], int] = field(default_factory=lambda: defaultdict(int))
    recircs: int = 0
    stage_locked: Set[int] = field(default_factory=set)
    res_stage: Dict[str, int] = field(default_factory=dict)

def upper_bound_worst_case(mg: MicroGraph) -> int:
    return max(0, len(mg.nodes)-1)

def lower_bound_min_recirc(mg: MicroGraph) -> int:
    counts = defaultdict(int)
    for n in mg.nodes.values():
        for r in n.reads.union(n.writes):
            if r.startswith("reg:") or r.startswith("hash:"):
                counts[r] += 1
    lb = 0
    for c in counts.values():
        lb = max(lb, max(0, c-1))
    return lb

def node_resources(n: MicroNode) -> Set[str]:
    return {r for r in n.reads.union(n.writes) if r.startswith("reg:") or r.startswith("hash:")}

def can_place(node: MicroNode, stage: Stage, flow: int, table: Table, placement: Placement) -> bool:
    if stage.index in placement.stage_locked and node.op != "WRITE_PHASE":
        return False
    if not node.requires.issubset(table.capabilities):
        return False
    key = (stage.index, flow, table.name)
    if placement.table_usage[key] >= table.capacity:
        return False
    for pred in node.preds:
        if pred in placement.node_to_slot:
            ps,_,_ = placement.node_to_slot[pred]
            if ps > stage.index:
                return False
    for res in node_resources(node):
        if res in placement.res_stage and placement.res_stage[res] != stage.index:
            return False
    return True

def place(node: MicroNode, stage: Stage, flow: int, table: Table, placement: Placement) -> Placement:
    newp = Placement(node_to_slot=dict(placement.node_to_slot),
                     table_usage=defaultdict(int, placement.table_usage),
                     recircs=placement.recircs,
                     stage_locked=set(placement.stage_locked),
                     res_stage=dict(placement.res_stage))
    key = (stage.index, flow, table.name)
    newp.node_to_slot[node.id] = (stage.index, flow, table.name)
    newp.table_usage[key] += 1
    if node.op == "WRITE_PHASE":
        newp.stage_locked.add(stage.index)
    for res in node_resources(node):
        if res not in newp.res_stage:
            newp.res_stage[res] = stage.index
    return newp

def bnb_place(mg: MicroGraph, stages: List[Stage], budget:int=8000, stop_at_zero=True) -> Optional[Placement]:
    order = mg.topo()
    best: Optional[Placement] = None
    best_ub = float("inf")

    def dfs(i:int, placement: Placement):
        nonlocal best, best_ub, budget
        if budget <= 0:
            return
        budget -= 1
        lb = lower_bound_min_recirc(mg)
        if lb >= best_ub:
            return
        if i == len(order):
            rec = placement.recircs
            if rec < best_ub:
                best, best_ub = placement, rec
            if stop_at_zero and rec == 0:
                raise StopIteration
            return
        nid = order[i]
        node = mg.nodes[nid]
        progressed = False
        for st in stages:
            for flow, tables in st.flows.items():
                for tab in tables:
                    if can_place(node, st, flow, tab, placement):
                        progressed = True
                        dfs(i+1, place(node, st, flow, tab, placement))
        if not progressed and (best is None or placement.recircs + 1 < best_ub):
            newp = Placement(node_to_slot=dict(placement.node_to_slot),
                             table_usage=defaultdict(int, placement.table_usage),
                             recircs=placement.recircs + 1,
                             stage_locked=set(placement.stage_locked),
                             res_stage=dict(placement.res_stage))
            dfs(i, newp)

    try:
        dfs(0, Placement())
    except StopIteration:
        pass
    return best

def build_shared_reg_demo() -> MicroGraph:
    mg = MicroGraph()
    # Program A
    mg.add(MicroNode("A_calc", "ALU", requires={"ALU"}, program="A"))
    mg.add(MicroNode("A_r", "REG_READ", reads={"reg:bf[five_t]"}, requires={"REG_READ"}, program="A"))
    mg.add(MicroNode("A_alu", "ALU", requires={"ALU"}, program="A"))
    mg.add(MicroNode("A_w", "REG_WRITE", writes={"reg:bf[five_t]"}, requires={"REG_WRITE"}, program="A"))
    mg.add(MicroNode("A_wp", "WRITE_PHASE", requires={"WRITE_PHASE"}, program="A"))
    mg.add_edge("A_calc", "A_r")
    mg.add_edge("A_r", "A_alu")
    mg.add_edge("A_alu", "A_w")
    mg.add_edge("A_w", "A_wp")
    # Program B
    mg.add(MicroNode("B_calc", "ALU", requires={"ALU"}, program="B"))
    mg.add(MicroNode("B_r", "REG_READ", reads={"reg:bf[five_t]"}, requires={"REG_READ"}, program="B"))
    mg.add(MicroNode("B_alu", "ALU", requires={"ALU"}, program="B"))
    mg.add(MicroNode("B_w", "REG_WRITE", writes={"reg:bf[five_t]"}, requires={"REG_WRITE"}, program="B"))
    mg.add(MicroNode("B_wp", "WRITE_PHASE", requires={"WRITE_PHASE"}, program="B"))
    mg.add_edge("B_calc", "B_r")
    mg.add_edge("B_r", "B_alu")
    mg.add_edge("B_alu", "B_w")
    mg.add_edge("B_w", "B_wp")
    return mg

if __name__ == "__main__":
    stages = build_pipeline(3)
    mg = build_shared_reg_demo()
    best = bnb_place(mg, stages, budget=8000, stop_at_zero=True)
    if best:
        print("Best recircs:", best.recircs)
        print("Resource-to-stage:", best.res_stage)
        for nid, (s,f,t) in sorted(best.node_to_slot.items(), key=lambda kv: kv[1]):
            print(f"{nid:8s} -> Stage {s} Flow {f} Table {t}")
    else:
        print("No feasible placement found.")
