# Compiler/py/stagerun_graph/graph_core.py
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Literal, Any

DepType = Literal["DATA", "CONTROL", "RESOURCE", "FALLTHROUGH"]

@dataclass
class StageRunEffect:
    """Effect (lê, escreve, usa) de uma instrução StageRun."""
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    uses: Set[str] = field(default_factory=set)

@dataclass
class StageRunNode:
    id: int
    instr: Any              # AST node original
    effect: StageRunEffect

@dataclass
class StageRunEdge:
    src: int
    dst: int
    dep: DepType

@dataclass
class StageRunGraph:
    graph_id: str
    nodes: Dict[int, StageRunNode] = field(default_factory=dict)
    edges: List[StageRunEdge] = field(default_factory=list)

    def add_node(self, node: StageRunNode):
        self.nodes[node.id] = node

    def add_edge(self, src: int, dst: int, dep: DepType):
        self.edges.append(StageRunEdge(src, dst, dep))
        # self.edges.append(StageRunEdge(src, dst, dep, label))
