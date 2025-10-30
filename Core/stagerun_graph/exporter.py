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

from Core.stagerun_graph.graph_core import StageRunGraph, StageRunNode, StageRunEdge
from Core.ast_nodes import IfNode, BooleanExpression


# ============================================================
# Helpers
# ============================================================

def _compute_checksum_bytes(data: bytes) -> str:
    """Compute SHA-256 checksum for byte data."""
    return hashlib.sha256(data).hexdigest()


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
            "op": "IF",
            "args": {
                "branches": branches,
                "else_body": else_body,
            },
        }

    # Generic path for dataclasses or objects with attributes
    op = type(instr).__name__
    try:
        args = dataclasses.asdict(instr)
    except TypeError:
        # Fallback: generic attribute extraction
        args = {
            k: v
            for k, v in vars(instr).items()
            if not k.startswith("_") and not callable(v)
        }

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
        "nodes": [_serialize_node(n) for n in graph.nodes.values()],
        "edges": [_serialize_edge(e) for e in graph.edges],
    }


# ============================================================
# Main Export Function
# ============================================================

def export_stage_run_graphs(
    program_name: str,
    graphs: list[StageRunGraph],
    resources: Dict[str, Any],
    output_path: str | Path,
    schema_version: int = 1.0
) -> str:
    """
    Export program graphs and resources into a JSON file with a checksum header.

    :param program_name: Name of the StageRun program (e.g., "ditto2")
    :param graphs: List of StageRunGraph objects
    :param resources: Dict with program resources (ports, queues, vars, etc.)
    :param output_path: Path to output JSON file
    :return: SHA-256 checksum string
    """
    payload = {
        "program": program_name,
        "schema_version": schema_version,
        "graphs": [_serialize_graph(g) for g in graphs],
        "resources": resources,
    }

    json_bytes = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
    checksum = _compute_checksum_bytes(json_bytes)

    output_path = Path(output_path)
    with output_path.open("wb") as f:
        f.write(checksum.encode("utf-8") + b"\n" + json_bytes)

    return checksum
