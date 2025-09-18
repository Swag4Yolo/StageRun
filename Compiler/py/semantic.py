# src/stagerun_compiler/semantic.py
from typing import List, Dict, Any
from ast_nodes import PortDecl, ForwardInstr

class SemanticError(Exception):
    pass

def semantic_check(ast_nodes: List, program_name: str) -> Dict[str, Any]:
    """
    - Collect declared ports (data).
    - Ensure no duplicate port names.
    - Ensure instructions reference declared ports.
    Returns IR dict with 'data' and 'instructions'.
    """
    ports = []
    port_set = set()
    instructions = []
    instr_id = 1

    print(ast_nodes)

    # First pass: collect ports
    for node in ast_nodes:

        print("node")
        print(node)

        if isinstance(node, PortDecl):
            print("PortDecl detected" )
            if node.name in port_set:
                raise SemanticError(f"Duplicate PORT '{node.name}' at line {node.lineno}")
            port_set.add(node.name)
            ports.append(node.name)

    # Second pass: build instructions; verify references
    for node in ast_nodes:
        if isinstance(node, ForwardInstr):
            if node.dest not in port_set:
                raise SemanticError(f"Undefined port '{node.dest}' referenced by FWD at line {node.lineno}")
            instructions.append({
                "id": instr_id,
                "op": "FWD",
                "args": {"dest": node.dest},
                "meta": {"lineno": node.lineno}
            })
            instr_id += 1

    ir = {
        "program": program_name,
        "compiler_version": "0.1.0",
        "schema_version": "1",
        "data": {
            "ports": ports
        },
        "instructions": instructions
    }
    return ir
