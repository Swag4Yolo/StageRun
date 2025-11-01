# Runtime/Controller/py/importer.py
import json
import hashlib
from pathlib import Path
from Core.stagerun_graph.graph_core import StageRunGraph, StageRunNode, StageRunEdge

def _compute_checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_stage_run_graphs(input_path: str | Path) -> dict:
    """
    Reads a StageRunGraph JSON with SHA-256 checksum header.
    Returns a dictionary { program, schema_version, graphs[], resources{} }.
    """
    input_path = Path(input_path)
    with input_path.open("rb") as f:
        checksum = f.readline().strip().decode("utf-8")
        blob = f.read()

    actual = _compute_checksum_bytes(blob)
    if actual != checksum:
        raise ValueError(f"Checksum mismatch in {input_path.name}")

    return json.loads(blob.decode("utf-8"))

def load_graph_objects(input_path: str | Path) -> list[StageRunGraph]:
    """
    Optionally reconstruct StageRunGraph objects (nodes/edges only).
    """
    data = load_stage_run_graphs(input_path)
    graphs = []
    for g in data["graphs"]:
        srg = StageRunGraph(graph_id=g["graph_id"])

        # 1. Add Keys
        srg.keys = g["keys"]
        # 2. Add Default Action
        srg.default_action = g["default_action"]
        # 3. Add Nodes
        for n in g["nodes"]:
            node = StageRunNode(
                id=n["id"],
                kind=n["kind"],
                instr=None,  # Controller não conhece AST original
                effect=n.get("effect"),
                # label=n.get("label")
            )
            srg.add_node(node)
        for e in g["edges"]:
            srg.add_edge(e["src"], e["dst"], e["dep"])
        graphs.append(srg)
    return graphs
