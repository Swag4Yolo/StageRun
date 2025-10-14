# src/stagerun_compiler/semantic.py
from typing import List, Dict, Any
from ast_nodes import (
    PortDecl,
    ForwardInstr,
    HeaderIncrementInstruction,
    KeyCondition,
    PreFilter,
)

class SemanticError(Exception):
    pass

# Which header fields we accept in KEYs and HINC (upper-cased for comparison)
SUPPORTED_HEADERS = {"IPV4.TTL", "IPV4.DST", "IPV4.SRC", "PKT.PORT"}

# Supported ops are limited: only equality for now
ALLOWED_KEY_OPS = {"=="}

# Supported instruction types (strings for IR)
FWD = "FWD"
HINC = "HINC"

def semantic_check(ast_nodes: List, program_name: str) -> Dict[str, Any]:
    """
    Semantic analysis for the simplified language where everything lives inside PREFILTERs
    (and PORT declarations).
    Produces an IR dict:
      {
        "program": <name>,
        "compiler_version": <>,
        "schema_version": <>,
        "data": {"ports": [...]},
        "prefilters": [ { name, keys:[{field,op,value,lineno}], default:{type,arg}/"DROP"/None, body:[{op,args,meta}] } ]
      }
    Raises SemanticError with a clear message and lineno when validation fails.
    """
    # Collect declared ports
    ports: List[str] = []
    port_set = set()
    for node in ast_nodes:
        if isinstance(node, PortDecl):
            if node.name in port_set:
                raise SemanticError(f"Duplicate PORT '{node.name}' at line {node.lineno}")
            ports.append(node.name)
            port_set.add(node.name)

    # No standalone instructions allowed (per your simplification): ensure only PortDecl and PreFilter nodes exist
    for node in ast_nodes:
        if not isinstance(node, (PortDecl, PreFilter)):
            raise SemanticError(f"Unexpected top-level node {type(node).__name__} at line {getattr(node, 'lineno', '?')}")

    prefilters_ir = []

    # Validate each Prefilter
    for node in ast_nodes:
        if isinstance(node, PreFilter):
            pf: PreFilter = node

            # Validate name is non-empty
            if not pf.name:
                raise SemanticError(f"Prefilter with empty name at line {pf.lineno}")

            # Validate keys (if any)
            keys_ir = []
            for k in pf.keys:
                if not isinstance(k, KeyCondition):
                    raise SemanticError(f"Invalid KEY node in PREFILTER '{pf.name}' at line {pf.lineno}")
                # op check
                if k.op not in ALLOWED_KEY_OPS:
                    raise SemanticError(f"Unsupported operator '{k.op}' in KEY at line {k.lineno}")
                # field should be NAME.NAME
                if "." not in k.field:
                    raise SemanticError(f"KEY field must be of the form NAME.NAME at line {k.lineno}")
                if k.field.upper() not in SUPPORTED_HEADERS:
                    raise SemanticError(f"Unsupported KEY field '{k.field}' at line {k.lineno}")
                # value: either a declared port or a literal (CIDR / IP / string)
                val = k.value
                if val in port_set:
                    # OK: reference to port
                    pass
                else:
                    # Allow CIDR-like (contains '/'), dotted IP-like (digits and dots), or any string literal (we strip quotes in parser)
                    if "/" in val or (any(ch.isdigit() for ch in val) and "." in val) or val.isnumeric():
                        pass
                    else:
                        # Could be a missing port or unknown identifier
                        raise SemanticError(f"Unknown reference '{val}' in KEY at line {k.lineno}")
                keys_ir.append({"field": k.field, "op": k.op, "value": val, "lineno": k.lineno})

            # Validate default (optional)
            default_ir = None
            if pf.default is None:
                default_ir = None
            elif isinstance(pf.default, ForwardInstr):
                # ensure port exists
                if pf.default.dest not in port_set:
                    raise SemanticError(f"Undefined port '{pf.default.dest}' in DEFAULT of PREFILTER '{pf.name}' at line {pf.default.lineno}")
                default_ir = {"type": FWD, "dest": pf.default.dest, "lineno": pf.default.lineno}
            elif isinstance(pf.default, str) and pf.default == "DROP":
                default_ir = {"type": "DROP", "lineno": pf.lineno}
            else:
                raise SemanticError(f"Invalid DEFAULT in PREFILTER '{pf.name}' at line {pf.lineno}")

            # Validate body (optional) - can contain ForwardInstr and HeaderIncrementInstruction
            body_ir = []
            for instr in pf.body:
                if isinstance(instr, ForwardInstr):
                    if instr.dest not in port_set:
                        raise SemanticError(f"Undefined port '{instr.dest}' in PREFILTER '{pf.name}' BODY at line {instr.lineno}")
                    body_ir.append({"op": FWD, "args": {"dest": instr.dest}, "meta": {"lineno": instr.lineno}})
                elif isinstance(instr, HeaderIncrementInstruction):
                    if instr.target.upper() not in SUPPORTED_HEADERS:
                        raise SemanticError(f"Unsupported header '{instr.target}' in PREFILTER '{pf.name}' BODY at line {instr.lineno}")
                    body_ir.append({"op": HINC, "args": {"target": instr.target, "value": instr.value}, "meta": {"lineno": instr.lineno}})
                else:
                    raise SemanticError(f"Unsupported instruction in PREFILTER '{pf.name}' BODY at line {getattr(instr, 'lineno', pf.lineno)}")

            prefilters_ir.append({
                "name": pf.name,
                "keys": keys_ir,
                "default": default_ir,
                "body": body_ir,
                "meta": {"lineno": pf.lineno}
            })

    # Build final IR
    ir = {
        "program": program_name,
        "compiler_version": 0.1,
        "schema_version": 1,
        "data": {"ports": ports},
        "prefilters": prefilters_ir
    }
    return ir
