from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any


# Other Imports
import re
import logging

# StageRun Imports
import lib.controller.state_manager as sm
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from lib.controller.constants import *


DepKind = Literal["DATA", "CONTROL", "CHOICE", "PHASE"]  # PHASE = write phase barrier

class MicroInstructionError(Exception):
    pass

@dataclass
class MicroEffect:
    """Represents read/write effects of a micro instruction."""
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    uses: Set[str] = field(default_factory=set)

    def merge(self, other: "MicroEffect") -> "MicroEffect":
        """Merge another MicroEffect into this one (for multi-step instructions)."""
        return MicroEffect(
            reads=self.reads | other.reads,
            writes=self.writes | other.writes,
            uses=self.uses | other.uses,
        )

@dataclass
class MicroInstruction:
    """Represents one atomic micro-operation installable on the switch."""
    name: str
    kwargs: Dict[str, Any]
    alternative: str | None = None
    used_alternative: bool | False = False

    def __repr__(self):
        args = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
        return f"MicroInstruction({self.name} {args})"


@dataclass
class MicroNode:
    # node id
    id: int

    #micro instr
    instr: MicroInstruction
    
    # read or write constrains
    effect: MicroEffect

    graph_id: str             
    parent_node_id: Optional[int] = None  

    # Planner
    allocated_stage: Optional[int] = None
    allocated_table: Optional[int] = None
    allocated_flow: Optional[int] = None  # 1 or 2
    flow_id: Optional[int] = None         

@dataclass
class MicroEdge:
    src: int
    dst: int
    dep: DepKind              # DATA, CONTROL, CHOICE, PHASE
    # label: Optional[str] = None  # e.g., "true", "else", "alt0", "alt1"


@dataclass
class MicroGraph:
    graph_id: str
    nodes: Dict[int, MicroNode] = field(default_factory=dict)
    edges: List[MicroEdge] = field(default_factory=list)
    keys: Dict | None = None
    default_action: Dict | None = None


    def debug_print(self, show_effects: bool = True, filepath: str = "MicroGraphs.log"):
        """Pretty-print for inspecting graph contents at runtime."""
        with open(filepath, "a") as f:
            
            def pprint(msg):
                f.write(f"{msg}\n")

            pprint("=" * 80)
            pprint(f" MicroGraph: {self.graph_id}")
            pprint("=" * 80)

            # Prefilter keys & default action
            if self.keys:
                pprint(" Prefilter Keys:")
                pprint(f" Keys: {self.keys}")
                # for k in self.keys:
                #     pprint(f"   - Key: '{k}' | Value: {self.keys[k]}")
            else:
                pprint(" Prefilter Keys: None")

            if self.default_action:
                pprint(f" Default Action: {self.default_action}")
            else:
                pprint(" Default Action: None")

            pprint("\n Nodes:")
            if not self.nodes:
                pprint("   (none)")
            else:
                for nid, node in sorted(self.nodes.items()):
                    instr = getattr(node.instr, "name", None) #or getattr(node, "instr", None)
                    table = getattr(node, "allocated_table", None)
                    flow = getattr(node, "allocated_flow", None)
                    stage = getattr(node, "allocated_stage", None)
                    selected_op = getattr(node, "selected_op", None)
                    effect = getattr(node, "effect", None)
                    pprint(f" ├─ Node {nid}: {instr or '(unknown)'}")
                    pprint(f" │    selected_op: {selected_op}")
                    pprint(f" │    stage={stage}, flow={flow}, table={table}")
                    if hasattr(node, 'flow_id'):
                        pprint(f" │    flow_id: {node.flow_id}")
                    kwargs = getattr(getattr(node, 'instr', None), 'kwargs', None)
                    if kwargs:
                        pprint(f" │    kwargs: {kwargs}")
                    if show_effects and effect:
                        r = getattr(effect, 'reads', [])
                        w = getattr(effect, 'writes', [])
                        u = getattr(effect, 'uses', [])
                        pprint(f" │    effect: reads={list(r)}, writes={list(w)}, uses={list(u)}")

            pprint("\n Edges:")
            if not self.edges:
                pprint("   (none)")
            else:
                for e in self.edges:
                    dep = getattr(e, "dep", "?")
                    label = getattr(e, "label", "")
                    pprint(f"   {e.src} --[{dep}]--> {e.dst} {f'({label})' if label else ''}")

            pprint("=" * 80)


    def to_dot(self, filename: str | None = None, show_effects: bool = False) -> str:
        """
        Export the MicroGraph to Graphviz DOT format.
        If filename is given, writes to file; otherwise returns the DOT string.
        """
        import html

        lines = []
        lines.append(f'digraph "{self.graph_id}" {{')
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style="rounded,filled", fillcolor=lightgray, fontname="monospace"];')

        # Prefilter metadata (keys + default action)
        label_meta = []
        if self.keys:
            label_meta.append("\\n".join([f"KEY {k['field']} == {k['value']}" for k in self.keys]))
        if self.default_action:
            da = self.default_action
            label_meta.append(f"DEFAULT {da['op']} {da.get('args',{})}")
        if label_meta:
            lines.append(f'  subgraph cluster_meta {{ label="Prefilter {self.graph_id}"; color=gray; style=dashed;')
            for i, l in enumerate(label_meta):
                lines.append(f'    meta{i} [label="{html.escape(l)}", shape=note, fillcolor=lightyellow];')
            lines.append('  }')

        # Nodes
        for nid, node in sorted(self.nodes.items()):
            instr = getattr(node.instr, "instr", None) or getattr(node, "instr", None)
            selected_op = getattr(node, "selected_op", None)
            stage = getattr(node, "allocated_stage", "?")
            flow = getattr(node, "allocated_flow", "?")
            flow_id = getattr(node, "flow_id", "?")
            kwargs = getattr(getattr(node, "instr", None), "kwargs", None) or {}
            label = f"{nid}: {instr or '(?)'}\\n"
            if selected_op:
                label += f"sel={selected_op}\\n"
            label += f"stage={stage}, flow={flow}, fid={flow_id}"
            if show_effects and getattr(node, "effect", None):
                eff = node.effect
                label += f"\\nR:{','.join(eff.reads)} W:{','.join(eff.writes)}"
            lines.append(f'  {nid} [label="{html.escape(label)}", fillcolor=white];')

        # Edges
        colors = {"DATA": "black", "CONTROL": "blue", "RECIRC": "red"}
        for e in self.edges:
            dep = getattr(e, "dep", "DATA")
            color = colors.get(dep, "gray")
            label = getattr(e, "label", "")
            lines.append(f'  {e.src} -> {e.dst} [color={color}, label="{dep}{":" + label if label else ""}"];')

        lines.append("}")
        dot = "\n".join(lines)

        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(dot)
            print(f"[MicroGraph] DOT file written: {filename}")
        return dot
    
