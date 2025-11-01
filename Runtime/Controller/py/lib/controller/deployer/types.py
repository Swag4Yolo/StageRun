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

@dataclass
class MicroNode:
    id: int
    
    instr: MicroInstruction

    graph_id: str             # from StageRun graph (i.e., Prefilter name)
    parent_node_id: Optional[int] = None  # StageRunNode.id that originated this node

    # Planner
    allocated_stage: Optional[int] = None
    allocated_table: Optional[int] = None
    allocated_flow: Optional[int] = None  # 1 or 2
    flow_id: Optional[int] = None         # runtime flow id, to be assigned by Planner

@dataclass
class MicroEdge:
    src: int
    dst: int
    dep: DepKind              # DATA, CONTROL, CHOICE, PHASE
    # label: Optional[str] = None  # e.g., "true", "else", "alt0", "alt1"

@dataclass
class ChoiceGroup:
    """
    Represents an OR between sub-paths. Planner must pick exactly one variant
    and connect src→first(variant) and last(variant)→dst accordingly.
    """
    entry_node: int
    exit_node: int
    variants: List[List[int]]  # list of node-id paths, each a variant

@dataclass
class MicroGraph:
    graph_id: str
    nodes: Dict[int, MicroNode] = field(default_factory=dict)
    edges: List[MicroEdge] = field(default_factory=list)
    choices: List[ChoiceGroup] = field(default_factory=list)
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
                    instr = getattr(node.instr, "instr", None) or getattr(node, "instr", None)
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

            if self.choices:
                pprint("\n ChoiceGroups:")
                for i, ch in enumerate(self.choices):
                    pprint(f"   ChoiceGroup {i}: {ch.variants}")
            else:
                pprint("\n ChoiceGroups: None")

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


@dataclass
class MicroAlternative:
    """
    Wrapper que representa alternativas equivalentes (mutuamente exclusivas).
    Cada variante é uma lista de MicroInstruction.
    O to_micro é quem transforma isto em nodes + ChoiceGroup.
    """
    variants: List[List[MicroInstruction]]

# @dataclass
# class LoweringResult:
#     graphs: List[MicroGraph]
#     next_id: int              # for global id allocator continuity


@dataclass
class PreFilterKeys:
    instr_name: str   # e.g. "set_pkt_id"
    kwargs: dict      # {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.1.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}

@dataclass
class DefaultAction:
    instr_name: str   # e.g. "set_pkt_id"
    kwargs: dict      # {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.1.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}

@dataclass
class MicroInstruction:
    instr_name: str   # sum_ni
    kwargs: dict      # {"program_id": pid, "header_update":1, "header_id": HEADER_IPV4_TTL, "const_val":instr['args']['value']}

@dataclass
class PreFilter:
    name: str
    keys: PreFilterKeys
    default_action: DefaultAction
    body: List[MicroInstruction]

    def show(self):
        print("Name:")
        print(self.name)

        print("Keys:")
        for key in self.keys:
            print(key)

        print("Default Action:")
        print(self.default_action)

        print("Body:")
        for instr in self.body:
            print(instr)

@dataclass
class InPort:
    name: str

@dataclass
class OutPort:
    name: str
    qset: str

@dataclass
class Qset:
    name: str
    type: str
    size:  int


@dataclass
class StageRunMicroProgram:
    name: str
    prefilters: List[PreFilter] = field(default_factory=list)
    ports_in:   List[InPort] = field(default_factory=list)
    ports_out:  List[OutPort] = field(default_factory=list)
    qsets:      List[Qset] = field(default_factory=list)
    # posfilters: List[PosFilter] = field(default_factory=list)

    def show(self):
        for prefilter in self.prefilters:
            prefilter.show()

