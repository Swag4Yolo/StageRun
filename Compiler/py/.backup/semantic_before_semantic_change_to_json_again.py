from typing import Dict, Any, List, Optional
from Core.ast_nodes import *
from Core.serializer import save_program


class SemanticError(Exception):
    pass


SUPPORTED_HEADERS = {"IPV4.TTL", "IPV4.ID", "IPV4.LEN"}


def semantic_check(program: ProgramNode, program_name: str):
    """Perform semantic validation, then delegate serialization."""

    # 1. Ensure Unique Port Names
    seen = set()
    duplicates = []
    qset_names = {qset.name for qset in getattr(program, "qsets", [])}
    out_port_names = []

        
    # === 1. Ensure unique port names ===

    # check all input ports
    for port in program.ports_in:
        if port.name in seen:
            duplicates.append(port.name)
        seen.add(port.name)

    # check all output ports
    for port in program.ports_out:
        if port.name in seen:
            duplicates.append(port.name)
        out_port_names.append(port.name)
        seen.add(port.name)

        if port.qset != "" and port.qset not in qset_names:
            port_name = getattr(port, "name", str(port))
            raise SemanticError(f"Queue set '{port.qset}' referenced by port '{port_name}' is not defined")

    if duplicates:
        dups = ", ".join(duplicates)
        raise SemanticError(f"Duplicate port name(s): {dups}")
    
    for qset in program.qsets:
        if qset.type not in ["RR", "PRIO"]:
            raise SemanticError(f"Unsupported QSET type: {qset.type} present in QSET {qset.name}")


    # === 2. Validate Prefilters ===
    for prefilter in program.prefilters:
        # 1. Validate Keys
        # 2. Validate Default Action
        # 3. Validate Body

        # --- default ---
        if prefilter.default_action:
            action = prefilter.default_action
            if isinstance(action, FwdInstr):
                if action.target not in out_port_names:
                    raise SemanticError(f"Port '{action.target}' not found as POUT port. Error on DEFAULT of PREFILTER '{prefilter.name}'")
            elif isinstance(action, FwdAndEnqueueInstr):
                if action.target not in out_port_names:
                    raise SemanticError(f"Port '{action.target}' not found as POUT port. Error on DEFAULT of PREFILTER '{prefilter.name}'")
                # TODO: validate qid ?
            elif isinstance(action, DropInstr):
                pass
            else:
                raise SemanticError(f"Unsupported DEFAULT instruction in PREFILTER '{prefilter.name}'")

        # --- body ---
        if prefilter.body:
            for instr in prefilter.body.instructions:
                if isinstance(instr, FwdInstr):
                    if instr.target not in out_port_names:
                        raise SemanticError(f"Undefined port '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                # TODO: add qid validation
                elif isinstance(instr, FwdAndEnqueueInstr):
                    if instr.target not in out_port_names:
                        raise SemanticError(f"Undefined port '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, HeaderIncrementInstr):
                    if instr.target not in SUPPORTED_HEADERS:
                        raise SemanticError(f"Unsupported header '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, AssignmentInstr):
                    if instr.target not in SUPPORTED_HEADERS:
                        raise SemanticError(f"Unsupported header '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, (DropInstr, FwdAndEnqueueInstr, HtoVarInstr, IfNode)):
                    continue
                elif isinstance(instr, CloneInstr):
                    if instr.target not in out_port_names:
                        raise SemanticError(f"Undefined port '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, PadToPatternInstr):
                    for el in instr.pattern:
                        if not type(el) == int:
                            raise SemanticError(f"Unsupported pattern for PADTTERN instruction in 'PREFILTER BODY '{prefilter.name}'")
                else:
                    raise SemanticError(f"Unsupported instruction '{type(instr).__name__}' in PREFILTER BODY '{prefilter.name}'")

    