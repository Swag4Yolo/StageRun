"""
StageRunGraph Exporter
----------------------

Exports StageRunGraph objects (and resources) into a clean, predictable JSON file
with a checksum header.

Each node in a graph follows the fixed schema:
{
    "id": int,
    "op": str,
    "args": dict,
    "effect": {
        "reads": [str],
        "writes": [str],
        "uses": [str]
    }
}
"""

from __future__ import annotations
import json
import hashlib
from pathlib import Path
from typing import Any, Dict
import dataclasses

from Core.stagerun_graph.graph_builder import StageRunGraphBuilder
from Core.stagerun_graph.graph_core import StageRunGraph, StageRunNode, StageRunEdge
from Core.ast_nodes import IfNode, BooleanExpression, ProgramNode
from Core.stagerun_isa import ISA

# ============================================================
# Helpers
# ============================================================

def _compute_checksum_bytes(data: bytes) -> str:
    """Compute SHA-256 checksum for byte data."""
    return hashlib.sha256(data).hexdigest()


def _flatten_blocks(body) -> tuple[list[Any], list[tuple[str, int]]]:
    """
    Returns:
      - flat instruction list (in label order)
      - label_sizes: list of (label, count) in the same order
    """
    flat = []
    label_sizes = []
    for blk in (body.blocks or []):
        instrs = blk.instructions or []
        label_sizes.append((blk.label, len(instrs)))
        flat.extend(instrs)
    return flat, label_sizes

def _serialize_labels(graph: StageRunGraph, label_sizes: list[tuple[str, int]]) -> Dict[str, Any]:
    """
    Return labels as a JSON map: { "<label>": [node, node, ...], ... }
    """
    nodes_sorted = sorted(graph.nodes.values(), key=lambda n: n.id)

    # Skip synthetic start node if present (instr=None)
    offset = 0
    if nodes_sorted and getattr(nodes_sorted[0], "instr", None) is None:
        offset = 1

    labels_out: Dict[str, Any] = {}
    cursor = offset

    for label, count in label_sizes:
        label_nodes = nodes_sorted[cursor:cursor + count]
        cursor += count
        labels_out[label] = [_serialize_node(n) for n in label_nodes]

    return labels_out

def _serialize_handler(graph: StageRunGraph, label_sizes: list[tuple[str, int]]) -> Dict[str, Any]:
    return {
        "id": graph.graph_id,
        "keys": graph.keys,
        "default_action": graph.default_action,
        "labels": _serialize_labels(graph, label_sizes),
        "edges": [_serialize_edge(e) for e in graph.edges],
    }

# ============================================================
# Boolean expression serialization
# ============================================================

def _serialize_bool_expr(expr: BooleanExpression):
    """Recursively serialize a BooleanExpression tree into JSON."""
    if expr is None:
        return None

    if isinstance(expr, BooleanExpression):
        return {
            "left": _serialize_bool_expr(expr.left) if isinstance(expr.left, BooleanExpression) else expr.left,
            "op": expr.op,
            "right": _serialize_bool_expr(expr.right) if isinstance(expr.right, BooleanExpression) else expr.right,
        }

    return expr


# ============================================================
# Instruction serialization
# ============================================================
_instructions_dict = {
    "FwdInstr": ISA.FWD,
    "DropInstr": ISA.DROP,
    "RtsInstr": ISA.RTS,
    "FwdAndEnqueueInstr": ISA.FWD_AND_ENQUEUE,
    "HeaderIncrementInstr": ISA.HINC,
    "HeaderAssignInstr": ISA.HASSIGN,
    "CopyHeaderToVarInstr": ISA.HTOVAR,
    "CopyHashToVarInstr": ISA.HASHTOVAR,
    "CopyVarToHeaderInstr": ISA.VTOHEADER,
    "RandomInstr": ISA.RAND,
    "TimeInstr": ISA.TIME,
    "MemoryGetInstr": ISA.MGET,
    "MemorySetInstr": ISA.MSET,
    "MemoryIncInstr": ISA.MINC,
    "BrCondInstr": ISA.BRCOND,
    "JmpInstr": ISA.JMP,
    "SubInstr": ISA.SUB,
    "SumInstr": ISA.SUM,
    "MulInstr": ISA.MUL,
    "IncInstr": ISA.INC,
    "PadToPatternInstr": ISA.PADTTERN,
    "CloneInstr": ISA.CLONE,
    "ActivateInstr": ISA.ACTIVATE,
    "InInstr": ISA.IN,
    "OutInstr": ISA.OUT,
}

def _serialize_instr(instr: Any) -> Dict[str, Any]:
    """
    Serialize any instruction object.
    Automatically extracts dataclass fields as args.
    Special cases (like IF) handled separately.
    """

    # Special handling for IF nodes
    if isinstance(instr, IfNode):
        branches = []
        for br in instr.branches:
            body_instrs = [_serialize_instr(i) for i in br.body]
            branches.append({
                "condition": _serialize_bool_expr(br.condition),
                "body": body_instrs,
            })
        else_body = None
        if instr.else_body:
            else_body = [_serialize_instr(i) for i in instr.else_body]
        return {
            "op": ISA.IF.value,
            "args": {
                "branches": branches,
                "else_body": else_body,
            },
        }

    # Generic path for dataclasses or objects with attributes
    try:
        op = _instructions_dict[type(instr).__name__].value
        args = dataclasses.asdict(instr)
    except:
        op = None
        args = None
    # try:
    # except TypeError:
    #     # Fallback: generic attribute extraction
    #     args = {
    #         k: v
    #         for k, v in vars(instr).items()
    #         if not k.startswith("_") and not callable(v)
    #     }

    return {"op": op, "args": args or {}}



# ============================================================
# Node / Edge / Graph Serialization
# ============================================================

def _serialize_node(node: StageRunNode) -> Dict[str, Any]:
    """Serialize a StageRunNode into JSON-safe dictionary."""
    # Handle instruction-based nodes

    if hasattr(node, "instr") and node.instr is not None:
        instr_data = _serialize_instr(node.instr)
        op = instr_data["op"]
        args = instr_data["args"]
    else:
        op = node.op
        args = node.args or {}

    return {
        "id": node.id,
        "op": op,
        "args": args,
        "effect": {
            "reads": sorted(node.effect.reads) if node.effect else [],
            "writes": sorted(node.effect.writes) if node.effect else [],
            "uses": sorted(node.effect.uses) if node.effect else [],
        },
    }


def _serialize_edge(edge: StageRunEdge) -> Dict[str, Any]:
    """Serialize an edge between nodes."""
    return {
        "src": edge.src,
        "dst": edge.dst,
        "dep": edge.dep,
    }


def _serialize_graph(graph: StageRunGraph) -> Dict[str, Any]:
    """Serialize a full StageRunGraph."""
    return {
        "graph_id": graph.graph_id,
        "keys": graph.keys,
        "default_action": graph.default_action,
        "nodes": [_serialize_node(n) for n in graph.nodes.values()],
        "edges": [_serialize_edge(e) for e in graph.edges],
    }

def _serialize_resources(program: ProgramNode):
    pin = [p.name for p in program.ports_in]
    pout = []
    # pout = [p.name for p in program.ports_out]
    qsets = {}

    for qset in program.qsets:
        qsets[qset.name] = {
            "type": qset.type, 
            "size": qset.size,
            "ports": []
            }

    for p in program.ports_out:
        pout.append(p.name)
        qset_name = p.qset
        if qset_name and qset_name in qsets:
            qsets[qset_name]["ports"].append(p.name)

    regs = [reg.name for reg in program.regs]
    vars = [var.name for var in program.vars]
    # hashes = [h[name] = h.args for h in program.hashes]
    hashes = dict()
    for h in program.hashes:
        hashes[h.name] = h.args
    resources = {
        "ingress_ports": pin,
        "egress_ports": pout,
        "queues": qsets,       # e.g., [{"port":"P1_OUT","qid":1}]
        # "hashes": program.hashes,
        "registers": regs,
        "vars": vars,
        "hashes": hashes
        # "clones": program.,
    }

    return resources

def _build_stagerun_graphs(program: ProgramNode):
    graphs = []
    label_sizes_by_handler = {}

    for h in program.handlers:
        keys = h.keys or []
        default_action = h.default_action if h.default_action else None

        flat_body = []
        label_sizes = []

        if h.body and getattr(h.body, "blocks", None) is not None:
            flat_body, label_sizes = _flatten_blocks(h.body)

        g = StageRunGraphBuilder(graph_id=h.name).build(keys, default_action, flat_body)
        graphs.append(g)
        label_sizes_by_handler[h.name] = label_sizes

    return graphs, label_sizes_by_handler

def _build_stagerun_resources(program: ProgramNode):
    # Build a resources summary for the controller/exporter
    resources = {
        "ingress_ports": program.ports_in,
        "egress_ports": program.ports_out,
        "queues": program.qsets,       # e.g., [{"port":"P1_OUT","qid":1}]
        # "hashes": program.hashes,
        "registers": program.regs,
        "vars": program.vars,
        # "clones": program.,
    }

    return resources
# ============================================================
# Main Export Function
# ============================================================

def export_stage_run_graphs(
    program: ProgramNode,
    program_name: str,
    output_path: str | Path,
    schema_version: int = 1.0
) -> str:
    """
    Export program graphs and resources into a JSON file with a checksum field.
    The checksum is computed over the JSON payload with the 'checksum' field removed.
    """

    # 1) Build handler graphs
    graphs, label_sizes_by_handler = _build_stagerun_graphs(program)

    # 2) Build payload WITHOUT checksum first
    payload = {
        "program": program_name,
        "isa_version": ISA.VERSION.value,
        "schema_version": schema_version,
        "handlers": [
            _serialize_handler(g, label_sizes_by_handler.get(g.graph_id, []))
            for g in graphs
        ],
        "resources": _serialize_resources(program),
    }

    # 3) Compute checksum over canonical JSON of payload WITHOUT checksum
    json_bytes_no_checksum = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
    checksum = _compute_checksum_bytes(json_bytes_no_checksum)

    # 4) Insert checksum into payload and serialize final JSON
    payload_with_checksum = {"checksum": checksum, **payload}
    json_bytes = json.dumps(payload_with_checksum, indent=2, sort_keys=False).encode("utf-8")

    # 5) Write output: force name out.json if output_path is a directory
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(json_bytes)

    return checksum
