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

class UndefinedVariableError(SemanticError):
    def __init__(self, handler, var):
        super().__init__(f"Undefined Variable '{var}' used in {handler}.")

class UndefinedHashError(SemanticError):
    def __init__(self, handler, var):
        super().__init__(f"Undefined Hash '{var}' used in {handler}.")

class UnsupportedHeaderError(SemanticError):
    def __init__(self, handler:str, header:str):
        super().__init__(f"Unsupported Header {header} used in {handler}.")

class UndefinedInPortError(SemanticError):
    def __init__(self, port:str):
        super().__init__(f"Undefined In Port {port}.")

class UndefinedOutPortError(SemanticError):
    def __init__(self, port:str):
        super().__init__(f"Undefined Out Port {port}.")

# -------------------------
# Supported Headers
# -------------------------

SUPPORTED_HEADERS = {"IPV4.TTL", "IPV4.ID", "IPV4.LEN", "IPV4.PROTO", "IPV4.DST", "IPV4.SRC", "TCP.ACKNO", "IPV4.IHL", "TCP.DATAOFFSET", "TCP.FLAGS"}


def _validate_ports(program: ProgramNode) -> tuple[List[str], List[str]]:
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

def _validate_in_port(program:ProgramNode, handler:str, port:str):
    pin = [p.name for p in program.ports_in]
    if port not in pin:
        raise UndefinedInPortError(port=port)
def _validate_out_port(program:ProgramNode, handler:str, port:str):
    pout = [p.name for p in program.ports_out]
    if port not in pout:
        raise UndefinedOutPortError(port=port)
def _validate_header(program:ProgramNode, handler:str, header:str):
    if header not in SUPPORTED_HEADERS:
        raise UnsupportedHeaderError(handler=handler, header=header)
def _validate_var(program:ProgramNode, handler:str, var:str):
    vars = [v.name for v in program.vars]
    if var not in vars:
        raise UndefinedVariableError(handler=handler, var=var)
def _validate_hash(program:ProgramNode, handler:str, hash:str):
    if hash not in program.hashes:
        raise UndefinedHashError(handler=handler, hash=hash)


def _validate_prefilter(program: ProgramNode, pf: HandlerNode, ports_in: Set[str], ports_out: Set[str]) -> Dict[str, Any]:
    # keys
    keys = []
    for k in pf.keys or []:
        if not isinstance(k, HandlerKey):
            raise SemanticError(f"PREFILTER '{pf.name}': invalid key entry")
        # field like "PKT.PORT" or "HDR.FIELD"
        field = k.field
        value = k.value
        # basic checks: port key must reference existing port names
        if field == "PKT.PORT":
            if value not in ports_in and value not in ports_out:
                raise SemanticError(f"PREFILTER '{pf.name}': KEY references unknown port '{value}'")
        keys.append({"field": field, "value": value})

    if pf.default_action:
        da = pf.default_action
        if isinstance(da, FwdInstr):
            _validate_out_port(program, pf.name, da.port)
        elif isinstance(da, FwdAndEnqueueInstr):
            _validate_out_port(program, pf.name, da.port)
        elif isinstance(da, DropInstr):
            pass
        else:
            raise SemanticError(f"PREFILTER '{pf.name}': unsupported DEFAULT instruction")

    # body checks (headers validity, ports existence)
    if pf.body and isinstance(pf.body, HandlerBodyNode):
        for instr in pf.body.instructions:
            if isinstance(instr, FwdInstr):
                _validate_out_port(program, pf.name, instr.port)
            elif isinstance(instr, FwdAndEnqueueInstr):
                _validate_out_port(program, pf.name, instr.port)
                # _validate_queue_port(program, pf.name, instr.target)
            elif isinstance(instr, DropInstr):
                pass
            elif isinstance(instr, HeaderAssignInstr):
                _validate_header(program, pf.name, instr.header)
            elif isinstance(instr, HeaderIncrementInstr):
                _validate_header(program, pf.name, instr.header)

            # Copy Instructions
            elif isinstance(instr, CopyHeaderToVarInstr):
                _validate_header(program, pf.name, instr.header)
                _validate_var(program, pf.name, instr.var)
            elif isinstance(instr, CopyHashToVarInstr):
                _validate_hash(program, pf.name, instr.hash)
                _validate_var(program, pf.name, instr.var)
            elif isinstance(instr, CopyVarToHeaderInstr):
                _validate_header(program, pf.name, instr.header)
                _validate_var(program, pf.name, instr.var)

            elif isinstance(instr, PadToPatternInstr):
                for pat in instr.pattern:
                    if pat < 64:
                        raise SemanticError(f"PREFILTER '{pf.name}': element present in PADTTERN cannot be under 64 => '{pat}'")
            else:
                # block-level structures (IfNode etc.) are allowed — CFG builder tratará depois
                # Se quiseres ser estrito: testar nomes de classe aqui.
                pass


def semantic_check(program: ProgramNode, program_name: str) -> Dict[str, Any]:
    """
    Validate ProgramNode. Return a dict containing 'resources' for the exporter.
    Raise SemanticError on failures.
    """
    ports_in_set, ports_out_set = _validate_ports(program)
    #TODO: implement functions for queues, hashes, registers, clones

    # validate prefilters independently
    for pf in program.prefilters or []:
        if not isinstance(pf, HandlerNode):
            raise SemanticError("Invalid prefilter node in AST")
        _validate_prefilter(program, pf, ports_in_set, ports_out_set)

# TODO LIST:
# 1. Copy Instructions
#    - Should validate if variable or hash exists along the program


