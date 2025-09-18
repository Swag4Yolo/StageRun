# src/stagerun_compiler/cli.py
import argparse
import os
import sys
from parser import parse_program
from semantic import semantic_check, SemanticError
from backend import emit_json
from lark.exceptions import UnexpectedInput


def compile_file(infile: str, outfile: str | None = None) -> int:
    if not os.path.exists(infile):
        print(f"Error: file not found: {infile}", file=sys.stderr)
        return 2

    if outfile is None:
        base = os.path.splitext(os.path.basename(infile))[0]
        outfile = base + ".stagerun.json"

    try:
        with open(infile, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading {infile}: {e}", file=sys.stderr)
        return 2

    # Parse
    try:
        ast = parse_program(text)
    except UnexpectedInput as e:
        print(f"Syntax error at line {e.line}, column {e.column}:", file=sys.stderr)
        print("   " + e.get_context(text), file=sys.stderr)
        return 2
    except Exception as e:
        print("Internal parse error:", e, file=sys.stderr)
        return 2


    program_name = os.path.splitext(os.path.basename(infile))[0]

    # Semantic checks and IR generation
    try:
        
        ir = semantic_check(ast, program_name)
    except SemanticError as e:
        print("Semantic Error:", e, file=sys.stderr)
        return 2

    # Emit
    try:
        emit_json(ir, outfile)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 2

    print(f"Compiled {infile} -> {outfile}")
    return 0

def main():
    parser = argparse.ArgumentParser(prog="stagerunc")
    parser.add_argument("source", help="Input .srun file")
    parser.add_argument("-o", "--out", help="Output path for bytecode JSON", default=None)
    args = parser.parse_args()
    return compile_file(args.source, args.out)

if __name__ == "__main__":
    raise SystemExit(main())
