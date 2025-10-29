#!/usr/bin/env python3
"""
StageRun Compiler Driver
- Parse .srun
- Semantic validation
- Build StageRunGraph(s) per PREFILTER body
- Export JSON (+ SHA-256 header) for the controller
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

# --- Ensure project root (StageRun/) is importable
ROOT_DIR = Path(__file__).resolve().parents[2]  # .../StageRun
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Imports from codebase
from Compiler.py.parser import parse_stagerun_program
from Compiler.py.semantic import semantic_check, SemanticError
from Core.stagerun_graph.graph_builder import StageRunGraphBuilder
from Core.stagerun_graph.exporter import export_stage_run_graphs

# Types
from Core.ast_nodes import ProgramNode  # only for type hints


def build_stage_run_graphs(program: ProgramNode, program_name: str):
    """Build one StageRunGraph per PREFILTER (only BODY statements are graphed)."""
    graphs = []
    for pf in program.prefilters:
        body = getattr(pf, "body", None)
        stmts = getattr(body, "instructions", []) if body else []
        # cf_id: program:prefilter
        cf_id = f"{program_name}:{pf.name}"
        builder = StageRunGraphBuilder(graph_id=cf_id)
        g = builder.build_from_instructions(pf.name, stmts)
        graphs.append(g)
    return graphs


def main():
    ap = argparse.ArgumentParser(description="StageRun Compiler")
    ap.add_argument("input", help=".srun source file")
    ap.add_argument("-o", "--out", required=True,
                    help="Output JSON path for StageRunGraph (with checksum header)")
    ap.add_argument("--program-name", default=None, help="Program name override (defaults to input stem)")
    ap.add_argument("--schema-version", type=int, default=1.0, help="IR schema version")
    args = ap.parse_args()

    src_path = Path(args.input).resolve()
    out_path = Path(args.out).resolve()
    program_name = args.program_name or src_path.stem

    try:
        with open(src_path, "r", encoding="utf-8") as f:
            srun_program = f.read()
    except Exception as e:
        print(f"Error reading {src_path}: {e}", file=sys.stderr)
        return 2

    # 1) Parse
    program: ProgramNode = parse_stagerun_program(srun_program)

    # 2) Semantic validation (returns resources for controller)
    try:
        sem_out = semantic_check(program, program_name)
    except SemanticError as e:
        print(f"Semantic Error: {e}", file=sys.stderr)
        sys.exit(1)

    resources = sem_out.get("resources", {})

    # 3) Build StageRunGraph(s)
    graphs = build_stage_run_graphs(program, program_name)

    # 4) Export JSON (+ checksum header)
    checksum = export_stage_run_graphs(
        graphs=graphs,
        output_path=out_path,
        program_name=program_name,
        schema_version=args.schema_version,
        resources=resources
    )

    print(f"✔ Compiled {src_path.name}")
    print(f"   → graphs: {len(graphs)} prefilter(s)")
    print(f"   → wrote: {out_path}")
    print(f"   → checksum: {checksum}")


if __name__ == "__main__":
    main()
