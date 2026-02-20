# Compiler/py/stagerun_graph/effect_registry.py
from .graph_core import StageRunEffect
from Core.ast_nodes import *

def _operand_reads(operand) -> set[str]:
    if not isinstance(operand, str):
        return set()
    if operand.isdigit():
        return set()
    if operand.startswith(("var:", "hdr:", "reg:")):
        return {operand}
    return {f"var:{operand}"}

def _collect_bool_expr_reads(expr: BooleanExpression | None) -> set[str]:
    if expr is None:
        return set()
    reads = set()
    stack = [expr]
    while stack:
        node = stack.pop()
        left = node.left
        right = node.right
        if isinstance(left, BooleanExpression):
            stack.append(left)
        else:
            reads |= _operand_reads(left)
        if isinstance(right, BooleanExpression):
            stack.append(right)
        else:
            reads |= _operand_reads(right)
    return reads

def effect_of_instr(instr) -> StageRunEffect:

    # --- PADTTERN ---
    if isinstance(instr, PadToPatternInstr):
        # altera o comprimento → len do header
        return StageRunEffect(writes={"hdr:IPV4.LEN"})#, uses={"pattern"})

    # --- HTOVAR ---
    if isinstance(instr, CopyHeaderToVarInstr):
        return StageRunEffect(
            reads={f"hdr:{instr.header}"},
            writes={f"var:{instr.var}"}
        )
    
    # --- HTOVAR ---
    if isinstance(instr, CopyVarToHeaderInstr):
        return StageRunEffect(
            reads={f"var:{instr.var}"},
            writes={f"hdr:{instr.header}"}
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
        return StageRunEffect(writes={f"hdr:{instr.header}"})

    if isinstance(instr, HeaderIncrementInstr):
        return StageRunEffect(reads={f"hdr:{instr.header}"}, writes={f"hdr:{instr.header}"})

    # --- HASH / RANDOM ---
    if isinstance(instr, CopyHashToVarInstr):
        return StageRunEffect(writes={f"var:{instr.var}"}, uses={f"hash:{instr.hash}"})

    if isinstance(instr, RandomInstr):
        return StageRunEffect(writes={f"var:{instr.var}"})

    # --- MEMORY ---
    if isinstance(instr, MemoryGetInstr):
        return StageRunEffect(
            reads={f"hash:{instr.index}"},
            writes={f"var:{instr.var}"},
            uses={f"{instr.acess_type}"}
        )

    if isinstance(instr, MemorySetInstr):
        return StageRunEffect(
            # reads=_operand_reads(instr.index) | _operand_reads(instr.value),
            reads={f"hash:{instr.index}"},
            writes={f"reg:{instr.reg}"},
            # uses={f"mem_set:{instr.reg}"}
        )

    if isinstance(instr, MemoryIncInstr):
        return StageRunEffect(
            reads={f"hash:{instr.index}"},
            # reads=_operand_reads(instr.index) | _operand_reads(instr.increment) | {f"reg:{instr.reg}"},
            writes={f"reg:{instr.reg}", f"var:{instr.var}"},
            uses={f"{instr.acess_type}"}
        )

    # --- ARITHMETIC ---
    if isinstance(instr, SubInstr):
        return StageRunEffect(
            reads={f"var:{instr.lvar}", f"var:{instr.rvar}"},
            writes={f"var:{instr.resvar}"}
        )

    if isinstance(instr, SumInstr):
        return StageRunEffect(
            reads={f"var:{instr.lvar}", f"var:{instr.rvar}"},
            writes={f"var:{instr.resvar}"}
        )

    if isinstance(instr, MulInstr):
        return StageRunEffect(
            reads={f"var:{instr.lvar}"},
            writes={f"var:{instr.resvar}"}
        )

    # --- CONDITIONALS ---
    if isinstance(instr, BrCondInstr):
        return StageRunEffect(reads=_collect_bool_expr_reads(instr.cond), uses={f"label:{instr.label}"})

    if isinstance(instr, IfNode):
        reads = set()
        writes = set()
        uses = set()

        for br in instr.branches:
            reads |= _collect_bool_expr_reads(br.condition)
            for inner in br.body:
                inner_eff = effect_of_instr(inner)
                reads |= inner_eff.reads
                writes |= inner_eff.writes
                uses |= inner_eff.uses

        if instr.else_body:
            for inner in instr.else_body:
                inner_eff = effect_of_instr(inner)
                reads |= inner_eff.reads
                writes |= inner_eff.writes
                uses |= inner_eff.uses

        return StageRunEffect(reads=reads, writes=writes, uses=uses)

    # # --- IF ---
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
        
    #     reads = set()
    #     writes = set()
    #     uses = set()

    #     # As variáveis lidas nas condições
    #     for br in instr.branches:
    #         if br.condition:
    #             vars = collect_vars(br.condition)
    #             reads |= {f"var:{v}" for v in vars}

    #         # Efeitos das instruções dentro do corpo
    #         for inner in br.body:
    #             inner_eff = effect_of_instr(inner)
    #             reads |= inner_eff.reads
    #             writes |= inner_eff.writes
    #             uses |= inner_eff.uses

    #     # ELSE body
    #     if instr.else_body:
    #         for inner in instr.else_body:
    #             inner_eff = effect_of_instr(inner)
    #             reads |= inner_eff.reads
    #             writes |= inner_eff.writes
    #             uses |= inner_eff.uses

    #     return StageRunEffect(reads=reads, writes=writes, uses=uses)


    print("NONE Instruction Detected")
    print(type(instr))

    return StageRunEffect()
