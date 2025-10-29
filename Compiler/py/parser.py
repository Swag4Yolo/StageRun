from pathlib import Path
from lark import Lark, Transformer, v_args, Token
from Core.ast_nodes import *

# Resolve path relative to this file (parser.py)
GRAMMAR_PATH = Path(__file__).parent / "grammar" / "stagerun_grammar.lark"

with open(GRAMMAR_PATH, "r") as f:
    GRAMMAR = f.read()

parser = Lark(GRAMMAR, start="start", parser="lalr")

@v_args(inline=True)
class StageRunTransformer(Transformer):
    """
    Transforms the Lark parse tree into a fully-typed AST (dataclasses only).
    Important: No Lark Token or Tree escapes this layer.
    """

    # --- Terminal normalization (remove quotes / cast ints) -----------------
    def NAME(self, t: Token):
        return str(t)

    def STRING(self, t: Token):
        # strip enclosing quotes
        s = str(t)
        return s[1:-1] if len(s) >= 2 and s[0] == s[-1] == '"' else s

    def INT(self, t: Token):
        return int(str(t))

    def SIGNED_INT(self, t: Token):
        return int(str(t))

    # --- Atoms: dotted refs -------------------------------------------------
    def header_ref(self, left, right):
        # "IPV4" "." "TTL" -> "IPV4.TTL"
        return f"{left}.{right}"

    def key_ref(self, left, right):
        # "PKT" "." "PORT" -> "PKT.PORT"
        return f"{left}.{right}"

    # --- Top-level program assembly ----------------------------------------
    def start(self, *statements):
        ports_in, ports_out, qsets, program_vars, regs, prefilters = [], [], [], [], [], []
        for s in statements:
            if isinstance(s, PortDecl):
                (ports_in if s.direction == "IN" else ports_out).append(s)
            elif isinstance(s, QueueSetDecl):
                qsets.append(s)
            elif isinstance(s, VarDecl):
                program_vars.append(s)
            elif isinstance(s, RegDecl):
                regs.append(s)
            elif isinstance(s, PreFilterNode):
                prefilters.append(s)
        return ProgramNode(
            ports_in=ports_in,
            ports_out=ports_out,
            qsets=qsets,
            vars=program_vars,
            regs=regs,
            prefilters=prefilters,
        )

    # --- Declarations -------------------------------------------------------
    def port_in_decl(self, name):
        # "PIN" NAME
        return PortDecl(direction="IN", name=str(name), qset="")

    def port_out_decl(self, name, *qset):
        # "POUT" NAME
        if not qset:
            return PortDecl(direction="OUT", name=str(name),qset="")
        return PortDecl(direction="OUT", name=str(name), qset=str(qset[0]))

    def qset_decl(self, name, port, size):
        # "QSET" NAME NAME INT
        return QueueSetDecl(name=str(name), type=str(port), size=int(size))

    def var_decl(self, name):
        # "VAR" NAME
        return VarDecl(name=str(name))

    # --- Prefilter + clauses ------------------------------------------------
    def key_clause(self, key_ref, op, val):
        return PreFilterKey(field=key_ref,  operand=op, value=str(val))

    def default_clause(self, instr):
        # instr já é, por exemplo, ForwardInstr ou DropInstruction
        return PreFilterDefault(instr=instr)

    def body_clause(self, *instrs):
        return BodyNode(instructions=list(instrs))

    def prefilter(self, name, *clauses):
        keys, default, body = [], None, None

        for c in clauses:
            if isinstance(c, PreFilterKey):
                print(c)
                keys.append(c)
            elif isinstance(c, PreFilterDefault):
                default = c.instr
            elif isinstance(c, BodyNode):
                body = c
        return PreFilterNode(name=str(name), keys=keys,
                            default_action=default, body=body)

    # --- Instructions -------------------------------------------------------
    def fwd_instr(self, target):
        return FwdInstr(target=str(target))
    
    def fwd_queue_instr(self, target, qid):
        return FwdAndEnqueueInstr(target=str(target), qid=int(qid))

    def drop_instr(self):
        return DropInstr()

    def assign_instr(self, hdr_ref, value):
        return AssignmentInstr(target=str(hdr_ref), value=int(value))

    def hinc_instr(self, hdr_ref, value):
        return HeaderIncrementInstr(target=str(hdr_ref), value=int(value))

    def htovar_instr(self, hdr_ref, varname):
        return HtoVarInstr(target=str(hdr_ref), var_name=str(varname))

    def paddtern_instr(self, *pattern):
        return PadToPatternInstr(pattern=pattern)

    def clone_instr(self, target):
        return CloneInstr(target=str(target))

    # --- IF / ELIF / ELSE / ENDIF ------------------------------------------
    def if_block(self, if_clause, *rest):
        branches = [ConditionBlock(condition=if_clause[0], body=if_clause[1])]
        else_body = None
        for part in rest:
            if isinstance(part, tuple):       # elif
                branches.append(ConditionBlock(condition=part[0], body=part[1]))
            elif isinstance(part, list):      # else
                else_body = part
        return IfNode(branches=branches, else_body=else_body)

    def if_clause(self, cond_text, *instrs):
        return (BooleanExpression(text=str(cond_text)), list(instrs))

    def elif_clause(self, cond_text, *instrs):
        return (BooleanExpression(text=str(cond_text)), list(instrs))

    def else_clause(self, *instrs):
        return list(instrs)

    # --- Boolean expressions → canonical string ----------------------------
    # We render a safe, fully-parenthesized textual form so semantics/IR
    # never see Tokens/Trees and the controller can parse/evaluate later.

    def bool_expr(self, x):        return str(x)
    def or_expr(self, a, b=None):
        # LALR may call with two or with fully reduced child; guard both.
        return f"({a}) || ({b})" if b is not None else str(a)
    def and_expr(self, a, b=None):
        return f"({a}) && ({b})" if b is not None else str(a)
    def not_expr(self, *args):
        if len(args) == 2 and str(args[0]) == "!":
            return f"!({args[1]})"
        return str(args[-1])
    def comparison(self, l, op, r):
        return f"({l} {op} {r})"
    # Note: each token has two properties: t.type and t.value
    def comp_op(self, t):          return str(t.type)
    def arith_val(self, x):        return str(x)
    def var_ref(self, name):       return str(name)

    # --- Default
    def __default__(self, data, children, meta):
        if len(children) == 1:
            return children[0]
        return children


def parse_stagerun_program(text: str) -> ProgramNode:
    tree = parser.parse(text)
    return StageRunTransformer().transform(tree)
