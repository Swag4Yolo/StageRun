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
        seen.add(port.name)

        qset_name = port.qset
        print("qset_name")
        print(qset_name)
        if qset_name != "" and qset_name not in qset_names:
            port_name = getattr(port, "name", str(port))
            raise SemanticError(f"Queue set '{qset_name}' referenced by port '{port_name}' is not defined")

    if duplicates:
        dups = ", ".join(duplicates)
        raise SemanticError(f"Duplicate port name(s): {dups}")
    

    # === 2. Validate Prefilters ===
    for prefilter in program.prefilters:
        # 1. Validate Keys
        # 2. Validate Default Action
        # 3. Validate Body

        # --- default ---
        if prefilter.default_action:
            action = prefilter.default_action
            if isinstance(action, ForwardInstr):
                if action.target not in program.ports_out:
                    raise SemanticError(f"Port '{action.target}' not found as POUT port. Error on DEFAULT of PREFILTER '{prefilter.name}'")
            elif isinstance(action, ForwardAndEnqueueInstr):
                if action.target not in program.ports_out:
                    raise SemanticError(f"Port '{action.target}' not found as POUT port. Error on DEFAULT of PREFILTER '{prefilter.name}'")
                # TODO: validate qid ?
            elif isinstance(action, DropInstruction):
                pass
            else:
                raise SemanticError(f"Unsupported DEFAULT instruction in PREFILTER '{prefilter.name}'")

        # --- body ---
        if prefilter.body:
            for instr in prefilter.body.instructions:
                if isinstance(instr, ForwardInstr):
                    if instr.target not in program.ports_out:
                        raise SemanticError(f"Undefined port '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                # TODO: add qid validation
                elif isinstance(instr, ForwardAndEnqueueInstr):
                    if instr.target not in program.ports_out:
                        raise SemanticError(f"Undefined port '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, HeaderIncrementInstruction):
                    if instr.target not in SUPPORTED_HEADERS:
                        raise SemanticError(f"Unsupported header '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, AssignmentInstruction):
                    if instr.target not in SUPPORTED_HEADERS:
                        raise SemanticError(f"Unsupported header '{instr.target}' in PREFILTER BODY '{prefilter.name}'")
                elif isinstance(instr, (DropInstruction, ForwardAndEnqueueInstr, HtoVarInstr, IfNode)):
                    continue
                else:
                    raise SemanticError(f"Unsupported instruction '{type(instr).__name__}' in PREFILTER BODY '{prefilter.name}'")
