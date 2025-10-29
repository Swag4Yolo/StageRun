# Compiler/py/stagerun_graph/effect_registry.py
from .graph_core import StageRunEffect

def effect_of_instr(instr) -> StageRunEffect:
    k = type(instr).__name__

    # --- PADTTERN ---
    # a tua classe real parece ser PadToPatternInstr (pelo JSON)
    if k in ("PadToPatternInstr", "PatternInstr", "PatternInstruction", "PadPatternInstr"):
        # altera o comprimento → len do header
        return StageRunEffect(writes={"hdr.IPV4.LEN"}, uses={"pattern"})

    # --- HTOVAR ---
    if k in ("HtoVarInstr", "HtoVarInstruction"):
        return StageRunEffect(
            reads={f"hdr.{instr.target}"},
            writes={f"var.{instr.var_name}"}
        )

    # --- FWD / FWD_AND_ENQUEUE / DROP / CLONE ---
    if k in ("ForwardInstr", "ForwardInstruction"):
        return StageRunEffect(uses={f"port:{instr.target}"})

    if k in ("FwdAndEnqueueInstr", "FwdAndEnqueueInstruction"):
        return StageRunEffect(uses={f"port:{instr.target}", f"queue:{instr.target}:{instr.qid}"})

    if k in ("DropInstr", "DropInstruction"):
        return StageRunEffect()

    if k in ("CloneInstr", "CloneInstruction"):
        # marca o uso do porto como recurso para serializar ordem se necessário
        dest = getattr(instr, "target", None) or getattr(instr, "dest", None)
        uses = {f"port:{dest}"} if dest else set()
        return StageRunEffect(uses=uses)

    # --- ASSIGN / HINC ---
    if k in ("AssignmentInstruction", "AssignInstr"):
        return StageRunEffect(writes={f"hdr.{instr.target}"})

    if k in ("HeaderIncrementInstruction", "HincInstr"):
        return StageRunEffect(reads={f"hdr.{instr.target}"}, writes={f"hdr.{instr.target}"})

    # --- IF ---
    if k in ("IfNode", "IfInstruction"):
        reads = {f"var.{v}"} if isinstance(getattr(instr, "read_vars", None), str) else {f"var.{v}" for v in (getattr(instr, "read_vars", []) or [])}
        return StageRunEffect(reads=reads)

    return StageRunEffect()
