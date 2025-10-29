# Compiler/py/stagerun_graph/exporter.py
# --------------------------------------
# Export StageRunGraph objects to a versioned JSON file with a SHA-256 checksum.
# The file format is:
#   <hex_sha256_of_json>\n
#   { ... json payload ... }
#
# Usage (from semantic.py or your driver):
#   from stagerun_graph.exporter import export_stage_run_graphs
#   checksum = export_stage_run_graphs(
#       graphs=[g1, g2],
#       output_path="Programs/Ditto/ditto2.graph.json",
#       program_name="ditto2",
#       schema_version=1,
#       resources={"ports": [...], "queues": [...]}  # optional
#   )
#
# Notes:
#  - We avoid pickling: JSON is auditable, diffable, and schema-versionable.
#  - We try to map common AST instruction types to (op, args). Unknown ones are
#    serialized with a generic fallback so the controller can still reject or log.

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import your dataclasses (types only, no runtime coupling)
from .graph_core import StageRunGraph, StageRunNode, StageRunEdge
from Core.ast_nodes import *

# -----------------------------
# Helpers
# -----------------------------

class ExporterError(Exception):
    pass

def _compute_checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _serialize_instr(instr):
    if isinstance(instr, PadToPatternInstr):
        return {"op": "PADTTERN", "args": {"pattern": instr.pattern}}
    if isinstance(instr, HtoVarInstr):
        return {"op": "HTOVAR", "args": {"target": instr.target, "var": instr.var_name}}
    if isinstance(instr, FwdInstr):
        return {"op": "FWD", "args": {"dest": instr.target}}
    if isinstance(instr, FwdAndEnqueueInstr):
        return {"op": "FWD_AND_ENQUEUE", "args": {"dest": instr.target, "qid": instr.qid}}
    if isinstance(instr, DropInstr):
        return {"op": "DROP", "args": {}}
    if isinstance(instr, CloneInstr):
        return {"op": "CLONE", "args": {"dest": instr.target}}
    if isinstance(instr, AssignmentInstr):
        return {"op": "ASSIGN", "args": {"target": instr.target, "value": instr.value}}
    if isinstance(instr, HeaderIncrementInstr):
        return {"op": "HINC", "args": {"target": instr.target, "value": instr.value}}
    if isinstance(instr, IfNode):
        branches = []
        for br in instr.branches:
            body_instrs = [_serialize_instr(i) for i in br.body]
            branches.append({
                "condition": br.condition.text,
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

    
    raise ExporterError(f"Cannot Export Unknowned Instruction :op: {type(instr).__name__}, args: repr: {repr(instr)}")

def _serialize_node(n: StageRunNode) -> Dict[str, Any]:
    # Extract op/args if it's an instruction; otherwise just emit the node kind.
    payload: Dict[str, Any] = {
        "id": n.id,
        "kind": n.kind,
        # "label": n.label,
        "effect": {
            "reads": sorted(list(n.effect.reads)),
            "writes": sorted(list(n.effect.writes)),
            "uses": sorted(list(n.effect.uses)),
        },
    }
    if n.instr is not None:
        payload.update(_serialize_instr(n.instr))
    return payload


def _serialize_edge(e: StageRunEdge) -> Dict[str, Any]:
    return {
        "src": e.src,
        "dst": e.dst,
        "dep": e.dep,
        # "label": e.label,
    }


def _serialize_graph(g: StageRunGraph) -> Dict[str, Any]:
    return {
        "graph_id": g.graph_id,
        "nodes": [_serialize_node(n) for n in g.nodes.values()],
        "edges": [_serialize_edge(e) for e in g.edges],
    }


def _assemble_payload(
    graphs: List[StageRunGraph],
    program_name: str,
    schema_version: int = 1,
    resources: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "program": program_name,
        "schema_version": schema_version,
        "graphs": [_serialize_graph(g) for g in graphs],
    }
    if resources:
        payload["resources"] = resources
    if meta:
        payload["meta"] = meta
    return payload


# -----------------------------
# Public API
# -----------------------------

def export_stage_run_graphs(
    graphs: List[StageRunGraph],
    output_path: str | Path,
    program_name: str,
    schema_version: int = 1,
    resources: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Export a list of StageRunGraph objects to a JSON file with a SHA-256 checksum header.

    Returns:
        checksum (hex string)
    """
    output_path = Path(output_path)
    payload = _assemble_payload(
        graphs=graphs,
        program_name=program_name,
        schema_version=schema_version,
        resources=resources,
        meta=meta,
    )

    json_bytes = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
    checksum = _compute_checksum_bytes(json_bytes)

    # File format: "<checksum>\n<json>"
    with output_path.open("wb") as f:
        f.write(checksum.encode("utf-8") + b"\n" + json_bytes)

    return checksum


def load_and_verify_graphs(input_path: str | Path) -> Dict[str, Any]:
    """
    Utility for the controller (or tests): load JSON and verify checksum.
    Returns the parsed JSON payload (dict). Raises ValueError on mismatch.
    """
    input_path = Path(input_path)
    with input_path.open("rb") as f:
        header = f.readline().strip().decode("utf-8")
        json_blob = f.read()
    actual = _compute_checksum_bytes(json_blob)
    if actual != header:
        raise ValueError(f"Checksum mismatch in {input_path}. expected={header} got={actual}")
    return json.loads(json_blob.decode("utf-8"))
