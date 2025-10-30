"""
semantic.py
- Pure semantic validation of the parsed ProgramNode
- Returns minimal 'resources' dict for the controller/exporter
- Raises SemanticError on invalid programs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Set

# Import AST types
from Core.ast_nodes import *

# -------------------------
# Errors
# -------------------------
class SemanticError(Exception):
    pass


SUPPORTED_HEADERS = {"IPV4.TTL", "IPV4.ID", "IPV4.LEN", "IPV4.PROTO"}


def _collect_ports(program: ProgramNode) -> tuple[List[str], List[str]]:
    pin = [p.name for p in program.ports_in]
    pout = [p.name for p in program.ports_out]

    # uniqueness across all ports
    seen: Set[str] = set()
    dups: List[str] = []
    for n in pin + pout:
        if n in seen:
            dups.append(n)
        seen.add(n)
    if dups:
        raise SemanticError(f"Duplicate port name(s): {', '.join(dups)}")
    return pin, pout


def _validate_prefilter(pf: PreFilterNode, ports_in: Set[str], ports_out: Set[str]) -> Dict[str, Any]:
    # keys
    keys = []
    for k in pf.keys or []:
        if not isinstance(k, PreFilterKey):
            raise SemanticError(f"PREFILTER '{pf.name}': invalid key entry")
        # field like "PKT.PORT" or "HDR.FIELD"
        field = k.field
        value = k.value
        # basic checks: port key must reference existing port names
        if field == "PKT.PORT":
            if value not in ports_in and value not in ports_out:
                raise SemanticError(f"PREFILTER '{pf.name}': KEY references unknown port '{value}'")
        keys.append({"field": field, "value": value})

    # default action (only DROP, FWD, FWD_AND_ENQUEUE are allowed here)
    default_action = None
    if pf.default_action is not None:
        da = pf.default_action
        
        if isinstance(da, FwdInstr):
            if da.port not in ports_out:
                raise SemanticError(f"PREFILTER '{pf.name}': DEFAULT FWD to undefined egress '{da.port}'")
            default_action = {"op": "FWD", "args": {"dest": da.port}}

        elif isinstance(da, FwdAndEnqueueInstr):
            if da.target not in ports_out:
                raise SemanticError(f"PREFILTER '{pf.name}': DEFAULT FWD_AND_ENQUEUE to undefined egress '{da.target}'")
            default_action = {"op": "FWD_AND_ENQUEUE", "args": {"dest": da.target, "qid": da.qid}}
        
        elif isinstance(da, DropInstr):
            default_action = {"op": "DROP", "args": {}}
        else:
            raise SemanticError(f"PREFILTER '{pf.name}': unsupported DEFAULT instruction")

    # body checks (headers validity, ports existence)
    if pf.body and isinstance(pf.body, BodyNode):
        for instr in pf.body.instructions:
            if isinstance(instr, FwdInstr):
                if instr.port not in ports_out:
                    raise SemanticError(f"PREFILTER '{pf.name}': FWD to undefined egress '{instr.port}'")
            elif isinstance(instr, FwdAndEnqueueInstr):
                if instr.target not in ports_out:
                    raise SemanticError(f"PREFILTER '{pf.name}': FWD_AND_ENQUEUE to undefined egress '{instr.target}'")
            elif isinstance(instr, DropInstr):
                pass
            elif isinstance(instr, HeaderAssignInstr):
                if instr.target not in SUPPORTED_HEADERS:
                    raise SemanticError(f"PREFILTER '{pf.name}': ASSIGN unsupported header '{instr.target}'")
            elif isinstance(instr, HeaderIncrementInstr):
                if instr.target not in SUPPORTED_HEADERS:
                    raise SemanticError(f"PREFILTER '{pf.name}': HINC unsupported header '{instr.target}'")
            elif isinstance(instr, HtoVarInstr):
                # allow any header here; If you want, restrict to SUPPORTED_HEADERS
                if instr.target not in SUPPORTED_HEADERS:
                    raise SemanticError(f"PREFILTER '{pf.name}': HTOVAR unsupported header '{instr.target}'")
            elif isinstance(instr, PadToPatternInstr):
                for pat in instr.pattern:
                    if pat < 64:
                        raise SemanticError(f"PREFILTER '{pf.name}': element present in PADTTERN cannot be under 64 => '{pat}'")
            else:
                # block-level structures (IfNode etc.) are allowed — CFG builder tratará depois
                # Se quiseres ser estrito: testar nomes de classe aqui.
                pass

    return {"name": pf.name, "keys": keys, "default": default_action}


def semantic_check(program: ProgramNode, program_name: str) -> Dict[str, Any]:
    """
    Validate ProgramNode. Return a dict containing 'resources' for the exporter.
    Raise SemanticError on failures.
    """
    ports_in_set, ports_out_set = _collect_ports(program)
    #TODO: implement functions for queues, hashes, registers, clones

    # validate prefilters independently
    for pf in program.prefilters or []:
        if not isinstance(pf, PreFilterNode):
            raise SemanticError("Invalid prefilter node in AST")
        _validate_prefilter(pf, ports_in_set, ports_out_set)

    # Build a resources summary for the controller/exporter
    resources = {
        "ingress_ports": ports_in_set,
        "egress_ports": ports_out_set,
        # leave the below to be extended by later passes:
        "queues": [],       # e.g., [{"port":"P1_OUT","qid":1}]
        "hashes": [],
        "registers": [],
        "clones": [],
    }

    return {"resources": resources}
