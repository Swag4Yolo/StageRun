# Save the code content explicitly (since __file__ is not defined in this environment)
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from copy import deepcopy

@dataclass
class Table:
    name: str
    capabilities: Set[str]
    capacity: int

@dataclass
class Stage:
    index: int
    tables: List['Table']

@dataclass
class Instr:
    kind: str
    reg: Optional[str] = None
    name: str = ""

@dataclass
class ProgQueue:
    name: str
    queue: List[Instr]

    def empty(self) -> bool:
        return len(self.queue) == 0

    def head(self) -> Optional[Instr]:
        return self.queue[0] if self.queue else None

    def pop_head(self) -> Instr:
        return self.queue.pop(0)

@dataclass
class PipeState:
    usage: Dict[Tuple[int,int], int] = field(default_factory=dict)
    wp_stages: Set[int] = field(default_factory=set)
    reg_stage: Dict[str, int] = field(default_factory=dict)
    last_slot_per_prog: Dict[str, Tuple[int,int]] = field(default_factory=dict)
    placements: Dict[Tuple[int,int], List[Tuple[str, str]]] = field(default_factory=dict)

def build_pipeline(num_stages: int = 3) -> List[Stage]:
    stages: List[Stage] = []
    for s in range(num_stages):
        tables = [
            Table(name=f"S{s}T0", capabilities={"ALU","REG_READ"}, capacity=3),
            Table(name=f"S{s}T1", capabilities={"REG_WRITE"}, capacity=2),
            Table(name=f"S{s}T2", capabilities={"WRITE_PHASE"}, capacity=2),
        ]
        stages.append(Stage(index=s, tables=tables))
    return stages

def stage_supports(instr: Instr, table: Table) -> bool:
    need_map = {"ALU":"ALU","REG_READ":"REG_READ","REG_WRITE":"REG_WRITE","WRITE_PHASE":"WRITE_PHASE"}
    return need_map[instr.kind] in table.capabilities

def compute_upper_bound(programs: List[ProgQueue]) -> int:
    longest = max((len(p.queue) for p in programs), default=0)
    return max(0, longest - 1)

def consume_wp(programs: List[ProgQueue], state: PipeState,
               stages: List[Stage], stage_idx: int, table_idx: int):
    new_programs = deepcopy(programs)
    new_state = deepcopy(state)
    new_state.wp_stages.add(stage_idx)
    table = stages[stage_idx].tables[table_idx]
    if "WRITE_PHASE" not in table.capabilities:
        return new_programs, new_state
    cap_key = (stage_idx, table_idx)
    used = new_state.usage.get(cap_key, 0)
    capacity = table.capacity
    for prog in new_programs:
        if used >= capacity:
            break
        if not prog.empty() and prog.head().kind == "WRITE_PHASE":
            prog.pop_head()
            used += 1
            new_state.usage[cap_key] = used
            new_state.placements.setdefault(cap_key, []).append((prog.name, "WP"))
    return new_programs, new_state

def consume_instr(programs: List[ProgQueue], state: PipeState,
                  stages: List[Stage], stage_idx: int, table_idx: int):
    new_programs = deepcopy(programs)
    new_state = deepcopy(state)
    table = stages[stage_idx].tables[table_idx]
    cap_key = (stage_idx, table_idx)
    used = new_state.usage.get(cap_key, 0)
    capacity = table.capacity
    progressed = False
    for prog in new_programs:
        if used >= capacity:
            break
        if prog.empty():
            continue
        instr = prog.head()
        if stage_idx in new_state.wp_stages and instr.kind != "WRITE_PHASE":
            continue
        if instr.kind == "WRITE_PHASE":
            continue
        if not stage_supports(instr, table):
            continue
        if prog.name in new_state.last_slot_per_prog:
            last_stage, last_table = new_state.last_slot_per_prog[prog.name]
            if last_stage == stage_idx and not (table_idx > last_table):
                continue
        if instr.kind in ("REG_READ","REG_WRITE") and instr.reg:
            if instr.reg in new_state.reg_stage:
                if new_state.reg_stage[instr.reg] != stage_idx:
                    continue
            else:
                new_state.reg_stage[instr.reg] = stage_idx
        prog.pop_head()
        used += 1
        new_state.usage[cap_key] = used
        new_state.last_slot_per_prog[prog.name] = (stage_idx, table_idx)
        new_state.placements.setdefault(cap_key, []).append((prog.name, instr.name or instr.kind))
        progressed = True
    return new_programs, new_state, progressed

def next_table_or_stage(programs: List[ProgQueue], state: PipeState,
                        stages: List[Stage],
                        stage_idx: int, table_idx: int,
                        recircs: int, upper_bound: int):
    if table_idx + 1 < len(stages[stage_idx].tables):
        return pipeline_branch(programs, state, stages, stage_idx, table_idx + 1, recircs, upper_bound)
    if stage_idx + 1 < len(stages):
        return pipeline_branch(programs, state, stages, stage_idx + 1, 0, recircs, upper_bound)
    if any(not p.empty() for p in programs):
        if recircs + 1 > upper_bound:
            return float("inf"), None
        return pipeline_branch(programs, state, stages, 0, 0, recircs + 1, upper_bound)
    return recircs, state

def pipeline_branch(programs: List[ProgQueue], state: PipeState,
                    stages: List[Stage],
                    stage_idx: int, table_idx: int,
                    recircs: int, upper_bound: int):
    # if finish instructions
    if all(p.empty() for p in programs):
        # return exception no more searching
        if recircs == 0:
            return 0, state
        return recircs, state
    # not possible
    if recircs > upper_bound:
        return float("inf"), None

    is_stage_wp = stage_idx in state.wp_stages
    is_wp_available = any((not p.empty()) and p.head().kind == "WRITE_PHASE" for p in programs)
    results = []

    # if one instr is wp
    if is_wp_available:
        # new wp
        if not is_stage_wp:
            progs1, state1 = consume_wp(programs, state, stages, stage_idx, table_idx)
            r1 = next_table_or_stage(progs1, state1, stages, stage_idx, table_idx, recircs, upper_bound)
            results.append(r1)
            progs2, state2, progressed = consume_instr(programs, state, stages, stage_idx, table_idx)
            if progressed:
                r2 = next_table_or_stage(progs2, state2, stages, stage_idx, table_idx, recircs, upper_bound)
            # this seem useless they are the same
            else:
                r2 = next_table_or_stage(programs, state, stages, stage_idx, table_idx, recircs, upper_bound)
            results.append(r2)
        else:
            # already a wp, only consume instrs
            progs3, state3 = consume_wp(programs, state, stages, stage_idx, table_idx)
            r3 = next_table_or_stage(progs3, state3, stages, stage_idx, table_idx, recircs, upper_bound)
            results.append(r3)
    else:
        if is_stage_wp:
            r = next_table_or_stage(programs, state, stages, stage_idx, table_idx, recircs, upper_bound)
            results.append(r)
        else:
            progs4, state4, progressed = consume_instr(programs, state, stages, stage_idx, table_idx)
            if progressed:
                r4 = next_table_or_stage(progs4, state4, stages, stage_idx, table_idx, recircs, upper_bound)
            else:
                r4 = next_table_or_stage(programs, state, stages, stage_idx, table_idx, recircs, upper_bound)
            results.append(r4)
    valid = [(r, s) for r, s in results if s is not None]
    if not valid:
        return float("inf"), None
    return min(valid, key=lambda x: x[0])

# out = Path("/mnt/data/pipeline_scheduler_complete.py")
# out.write_text(code_text, encoding="utf-8")
# print(f"Saved: {out}")