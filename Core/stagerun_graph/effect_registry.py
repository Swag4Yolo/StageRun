# Compiler/py/stagerun_graph/effect_registry.py
from .graph_core import StageRunEffect
from Core.ast_nodes import *

def effect_of_instr(instr) -> StageRunEffect:

    # --- PADTTERN ---
    if isinstance(instr, PadToPatternInstr):
        # altera o comprimento → len do header
        return StageRunEffect(writes={"hdr.IPV4.LEN"})#, uses={"pattern"})

    # --- HTOVAR ---
    if isinstance(instr, CopyHeaderToVarInstr):
        return StageRunEffect(
            reads={f"hdr.{instr.target}"},
            writes={f"var.{instr.var_name}"}
        )

    # --- FWD / FWD_AND_ENQUEUE / DROP / CLONE ---
    if isinstance(instr, FwdInstr):
        return StageRunEffect(uses={f"port:{instr.port}"})

    if isinstance(instr, FwdAndEnqueueInstr):
        return StageRunEffect()
        # return StageRunEffect(uses={f"port:{instr.target}", f"queue:{instr.target}:{instr.qid}"})

    if isinstance(instr, DropInstr):
        return StageRunEffect()

    if isinstance(instr, CloneInstr):
        return StageRunEffect()
        # dest = getattr(instr, "target", None) or getattr(instr, "dest", None)
        # uses = {f"port:{dest}"} if dest else set()
        # return StageRunEffect(uses=uses)

    # --- ASSIGN / HINC ---
    if isinstance(instr, HeaderAssignInstr):
        return StageRunEffect(writes={f"hdr.{instr.header}"})

    if isinstance(instr, HeaderIncrementInstr):
        return StageRunEffect(reads={f"hdr.{instr.header}"}, writes={f"hdr.{instr.header}"})

    # --- IF ---
    if isinstance(instr, IfNode):
        def collect_vars(expr: BooleanExpression) -> set[str]:
            """Recursively collect variable names used in a BooleanExpression."""
            if expr is None:
                return set()
            vars = set()
            # Caso base: left/right são strings
            if isinstance(expr.left, str) and not expr.left.isdigit():
                vars.add(expr.left)
            if isinstance(expr.right, str) and not expr.right.isdigit():
                vars.add(expr.right)
            # Caso recursivo: sub-expressões
            if isinstance(expr.left, BooleanExpression):
                vars |= collect_vars(expr.left)
            if isinstance(expr.right, BooleanExpression):
                vars |= collect_vars(expr.right)
            return vars
        
        reads = set()
        writes = set()
        uses = set()

        # As variáveis lidas nas condições
        for br in instr.branches:
            if br.condition:
                vars = collect_vars(br.condition)
                reads |= {f"var.{v}" for v in vars}

            # Efeitos das instruções dentro do corpo
            for inner in br.body:
                inner_eff = effect_of_instr(inner)
                reads |= inner_eff.reads
                writes |= inner_eff.writes
                uses |= inner_eff.uses

        # ELSE body
        if instr.else_body:
            for inner in instr.else_body:
                inner_eff = effect_of_instr(inner)
                reads |= inner_eff.reads
                writes |= inner_eff.writes
                uses |= inner_eff.uses

        return StageRunEffect(reads=reads, writes=writes, uses=uses)
    # if isinstance(instr, IfNode):
    #     def collect_vars(expr: BooleanExpression) -> set[str]:
    #         """Recursively collect variable names used in a BooleanExpression."""
    #         if expr is None:
    #             return set()
    #         vars = set()
    #         # Caso base: left/right são strings
    #         if isinstance(expr.left, str) and not expr.left.isdigit():
    #             vars.add(expr.left)
    #         if isinstance(expr.right, str) and not expr.right.isdigit():
    #             vars.add(expr.right)
    #         # Caso recursivo: sub-expressões
    #         if isinstance(expr.left, BooleanExpression):
    #             vars |= collect_vars(expr.left)
    #         if isinstance(expr.right, BooleanExpression):
    #             vars |= collect_vars(expr.right)
    #         return vars

    #     read_vars = set()
    #     for br in instr.branches:
    #         read_vars |= collect_vars(br.condition)
    #     # if instr.else_body:
    #     #     pass  # else não lê variáveis
    #     return StageRunEffect(reads={f"var.{v}" for v in read_vars})


    return StageRunEffect()
