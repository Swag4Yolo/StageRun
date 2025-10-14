# src/stagerun_compiler/semantic.py
from typing import List, Dict, Any, Optional
from ast_nodes import _Ast
from ast_nodes import *

class SemanticError(Exception):
    pass

SUPPORTED_HEADERS = {"IPV4.TTL"}

def semantic_check(ast_nodes: List[_Ast], program_name: str) -> Dict[str, Any]:
    ports: List[str] = []
    port_set = set()
    instructions: List[Dict[str, Any]] = []
    instr_id = 1
    prefilters: List[Dict[str, Any]] = []

    print("ast_nodes:")
    print(ast_nodes)

    # 1. Collect ports
    for node in ast_nodes:
        if isinstance(node, PortDecl):
            if node.name in port_set:
                raise SemanticError(f"Duplicate PORT '{node.name}'")
            port_set.add(node.name)
            ports.append(node.name)

    # 2. Process Prefilters
    for node in ast_nodes:
        if isinstance(node, PreFilter):
            keys = []
            for k in node.keys:
                keys.append({"field": k.field, "value": k.value})

            default_action: Optional[Dict[str, Any]] = None
            if node.default:
                action = node.default.action
                if isinstance(action, ForwardInstr):
                    if action.dest not in port_set:
                        raise SemanticError(f"Undefined port '{action.dest}' in DEFAULT of PREFILTER '{node.name}'")
                    default_action = {"op": "FWD", "args": {"dest": action.dest}}
                elif isinstance(action, DropInstr):
                    default_action = {"op": "DROP", "args": {}}
                else:
                    raise SemanticError(f"Unsupported DEFAULT instruction in PREFILTER '{node.name}'")

            body_instructions: List[Dict[str, Any]] = []
            if node.body:
                print ("node.body.statements")
                print (node.body.statements)
                for instr in node.body.statements:

                    if isinstance(instr, ForwardInstr):
                        if instr.dest not in port_set:
                            raise SemanticError(f"Undefined port '{instr.dest}' in PREFILTER BODY '{node.name}'")
                        body_instructions.append({"id": instr_id, "op": "FWD", "args": {"dest": instr.dest}})
                    elif isinstance(instr, HeaderIncrementInstruction):
                        if instr.target not in SUPPORTED_HEADERS:
                            raise SemanticError(f"Unsupported header field '{instr.target}' in PREFILTER BODY '{node.name}'")
                        body_instructions.append({"id": instr_id, "op": "HINC", "args": {"target": instr.target, "value": instr.value}})
                    elif isinstance(instr, DropInstr):
                        body_instructions.append({"id": instr_id, "op": "DROP", "args": {}})
                    else:
                        raise SemanticError(f"Unsupported instruction in PREFILTER BODY '{node.name}'")
                    instr_id += 1

            prefilters.append({
                "name": node.name,
                "keys": keys,
                "default": default_action,
                "body": body_instructions
            })

    ir = {
        "program": program_name,
        "compiler_version": 0.1,
        "schema_version": 1,
        "data": {"ports": ports},
        "prefilters": prefilters
    }
    return ir
