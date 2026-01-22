
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
    return True

def place(node: MicroNode, stage: Stage, flow: int, table: Table, placement: Placement) -> Placement:
    newp = Placement(node_to_slot=dict(placement.node_to_slot),
                     table_usage=defaultdict(int, placement.table_usage),
                     recircs=placement.recircs,
                     stage_locked=set(placement.stage_locked))
    key = (stage.index, flow, table.name)
    newp.node_to_slot[node.id] = (stage.index, flow, table.name)
    newp.table_usage[key] += 1
    if node.op == "WRITE_PHASE":
        newp.stage_locked.add(stage.index)
    return newp

def bnb_place(mg: MicroGraph, stages: List[Stage], budget:int=2000, stop_at_zero=True) -> Optional[Placement]:
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
                             stage_locked=set(placement.stage_locked))
            dfs(i, newp)
    try:
        dfs(0, Placement())
    except StopIteration:
        pass
    return best

# Pipeline-driven

@dataclass
class Instr:
    kind: str                   # 'ALU','REG_READ','REG_WRITE','WRITE_PHASE'
    reg: Optional[str] = None

@dataclass
class ProgQueue:
    name: str
    queue: List[Instr]

@dataclass
class PipeState:
    placed: Dict[int, List[Instr]] = field(default_factory=lambda: defaultdict(list))
    write_phase: Set[int] = field(default_factory=set)
    regs_alloc: Dict[str, int] = field(default_factory=dict)

def stage_supports(instr: Instr, table: Table) -> bool:
    need = {
        "ALU": "ALU",
        "REG_READ": "REG_READ",
        "REG_WRITE": "REG_WRITE",
        "WRITE_PHASE": "WRITE_PHASE"
    }[instr.kind]
    return need in table.capabilities

def pipeline_branch(stage_idx:int, stages:List[Stage], progs:List[ProgQueue],
                    state:PipeState, recircs:int, budget:int=4000, stop_at_zero=True) -> Tuple[int, PipeState]:
    if budget <= 0:
        return (10**9, state)
    budget -= 1

    # if there is no more instrs to process, it is over
    if all(len(p.queue)==0 for p in progs):
        return (recircs, state)

    # check if current stage is WP
    S = stages[stage_idx % len(stages)]
    only_wp = (S.index in state.write_phase)
    head_is_wp = any(p.queue and p.queue[0].kind == "WRITE_PHASE" for p in progs)
    results = []

    # Branch A: consume WP now
    if head_is_wp and not only_wp:
        progs_A = deepcopy(progs)
        state_A = deepcopy(state)
        consumed = False
        for p in progs_A:
            if p.queue and p.queue[0].kind == "WRITE_PHASE":
                p.queue.pop(0)
                consumed = True
        if consumed:
            state_A.write_phase.add(S.index)
            results.append(pipeline_branch(stage_idx+1, stages, progs_A, state_A, recircs, budget, stop_at_zero))
    # elif head_is_wp and only_wp aproveita e processa os nos wp e continua

    # Branch B: try to place one instr per program at this stage
    progs_B = deepcopy(progs)
    state_B = deepcopy(state)
    progressed = False
    for p in progs_B:
        if not p.queue:
            continue
        instr = p.queue[0]
        if only_wp and instr.kind != "WRITE_PHASE":
            continue
        placed_here = False
        for flow, tables in S.flows.items():
            for tab in tables:
                if stage_supports(instr, tab):
                    if instr.kind in ("REG_READ","REG_WRITE") and instr.reg:
                        if instr.reg in state_B.regs_alloc:
                            reg_stage = state_B.regs_alloc[instr.reg]
                            if reg_stage < S.index:
                                # need recirc; cannot place this instr now
                                continue
                        else:
                            state_B.regs_alloc[instr.reg] = S.index  # greedy choice
                    state_B.placed[S.index].append(instr)
                    p.queue.pop(0)
                    placed_here = True
                    progressed = True
                    break
            if placed_here:
                break

    next_recircs = recircs
    next_stage_idx = stage_idx + 1
    if not progressed and not head_is_wp:
        next_recircs += 1
        next_stage_idx = 0

    results.append(pipeline_branch(next_stage_idx, stages, progs_B, state_B, next_recircs, budget, stop_at_zero))

    best_res = min(results, key=lambda x: x[0])
    if stop_at_zero and best_res[0] == 0:
        return best_res
    return best_res

# Demo builders

def demo_build_micrograph_for_bnb() -> MicroGraph:
    mg = MicroGraph()
    mg.add(MicroNode("calc_idx", "ALU", requires={"ALU"}))
    mg.add(MicroNode("read_bf", "REG_READ", reads={"reg:bf[five_t]"}, requires={"REG_READ"}))
    mg.add(MicroNode("cmp", "ALU", requires={"ALU"}))
    mg.add(MicroNode("write_bf", "REG_WRITE", writes={"reg:bf[five_t]"}, requires={"REG_WRITE"}))
    mg.add(MicroNode("wp", "WRITE_PHASE", requires={"WRITE_PHASE"}))
    mg.add_edge("calc_idx", "read_bf")
    mg.add_edge("read_bf", "cmp")
    mg.add_edge("cmp", "write_bf")
    mg.add_edge("write_bf", "wp")
    return mg

def demo_build_queues_for_pipeline() -> List[ProgQueue]:
    A = ProgQueue("A", [
        Instr("ALU"),
        Instr("REG_READ", reg="reg:bf[five_t]"),
        Instr("ALU"),
        Instr("REG_WRITE", reg="reg:bf[five_t]"),
        Instr("WRITE_PHASE"),
    ])
    B = ProgQueue("B", [
        Instr("ALU"),
        Instr("REG_READ", reg="reg:bf[five_t]"),
        Instr("ALU"),
        Instr("REG_WRITE", reg="reg:bf[five_t]"),
        Instr("WRITE_PHASE"),
    ])
    return [A, B]

if __name__ == "__main__":
    stages = build_pipeline(3)

    # Branch-and-Bound demo
    mg = demo_build_micrograph_for_bnb()
    sol = bnb_place(mg, stages, budget=2000, stop_at_zero=True)
    if sol:
        print("BnB best recircs:", sol.recircs)
        for nid, (s,f,t) in sol.node_to_slot.items():
            print(f"  {nid:10s} -> Stage {s} Flow {f} Table {t}")
    else:
        print("BnB found no solution.")

    print("\n" + "="*60 + "\n")

    # Pipeline-driven demo
    progs = demo_build_queues_for_pipeline()
    r, s = pipeline_branch(0, stages, progs, PipeState(), recircs=0, budget=4000, stop_at_zero=True)
    print("Pipeline best recircs:", r)
    for st in sorted(s.placed):
        kinds = [i.kind + (f"[{i.reg}]" if i.reg else "") for i in s.placed[st]]
        wp = " +WP" if st in s.write_phase else ""
        print(f"  Stage {st}{wp}: {', '.join(kinds) if kinds else '(none)'}")

