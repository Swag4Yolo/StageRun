from pathlib import Path
from lark import Lark, Transformer, v_args, Token
from Core.ast_nodes import *
import ipaddress
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
        return TypedRef(f"{left}.{right}", "header_ref")

    def key_ref(self, left, right):
        # "PKT" "." "PORT" -> "PKT.PORT"
        return f"{left}.{right}"

    def hash_ref(self, name):
        return TypedRef(str(name), "hash_ref")

    def reg_ref(self, name):
        return TypedRef(str(name), "reg_ref")

    # --- Top-level program assembly ----------------------------------------
    def start(self, *statements):
        ports_in, ports_out, qsets, setups, program_vars, regs, handlers, hashes = [], [], [], [], [], [], [], []
        for s in statements:
            if isinstance(s, PortDecl):
                (ports_in if s.direction == "IN" else ports_out).append(s)
            elif isinstance(s, QueueSetDecl):
                qsets.append(s)
            elif isinstance(s, SetupDecl):
                setups.append(s)
            elif isinstance(s, VarDecl):
                program_vars.append(s)
            elif isinstance(s, RegDecl):
                regs.append(s)
            elif isinstance(s, HashDecl):
                hashes.append(s)
            elif isinstance(s, HandlerNode):
                handlers.append(s)
        return ProgramNode(
            ports_in=ports_in,
            ports_out=ports_out,
            queues=qsets,
            setups=setups,
            vars=program_vars,
            regs=regs,
            hashes=hashes,
            handlers=handlers,
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

    def qset_decl(self, name, port, type, size):
        # "QSET" NAME NAME INT
        return QueueSetDecl(name=str(name), port=str(port), type=type, size=int(size))

    def setup(self, setup_decl):
        return setup_decl

    def loop_setup(self, out_port, in_port):
        return LoopSetupDecl(out_port=str(out_port), in_port=str(in_port))

    def pattern_setup(self, name, *pattern):
        return PatternSetupDecl(name=str(name), pattern=[int(p) for p in pattern])

    def var_decl(self, name):
        # "VAR" NAME
        return VarDecl(name=str(name))

    def hash_decl(self, name, *refs):
        # "HASH" NAME
        return HashDecl(name=str(name), args=refs)
    
    def reg_decl(self, name):
        # "HASH" NAME
        return RegDecl(name=str(name))
    
    def label_decl(self, name):
        return LabelDecl(name=str(name))
    

    # --- Handler + clauses ------------------------------------------------
    def key_clause(self, key_ref, op, val):
        return HandlerKey(field=key_ref,  operand=op, value=val)

    def default_clause(self, instr):
        # instr já é, por exemplo, ForwardInstr ou DropInstruction
        return HandlerDefault(instr=instr)

    def pos_key_clause(self, key_ref, op, val):
        return HandlerPosKey(field=key_ref, operand=op, value=val)

    def pos_default_clause(self, instr):
        return HandlerPosDefault(instr=instr)

    def pos_clause(self, pos_key, *_rest):
        pos_default = None
        for item in _rest:
            if isinstance(item, HandlerPosDefault):
                pos_default = item
                break
        return HandlerPosClause(key=pos_key, default_action=pos_default.instr)

    def body_clause(self, label_decl, *items):
        instrs = [x for x in items if x is not None]
        return BasicBlockNode(label=label_decl.name, instructions=instrs)
    
    def handler(self, name, *clauses):
        keys, default = [], None
        pos_clauses = []
        blocks = []

        for c in clauses:
            if isinstance(c, HandlerKey):
                keys.append(c)
            elif isinstance(c, HandlerDefault):
                default = c.instr
            elif isinstance(c, HandlerPosClause):
                pos_clauses.append(c)
            elif isinstance(c, BasicBlockNode):
                blocks.append(c)

        body = HandlerBodyNode(blocks=blocks) if blocks else None
        return HandlerNode(name=str(name), keys=keys, default_action=default, pos_clauses=pos_clauses, body=body)

    # --- Instructions: Forwarding -------------------------------------------
    def fwd_instr(self, target):
        return FwdInstr(port=str(target))
    
    def fwd_queue_instr(self, target, qid):
        target_str = str(target)
        return FwdAndEnqueueInstr(qname=target_str, port=target_str, qid=int(qid))

    def drop_instr(self):
        return DropInstr()
    
    def rts_instr(self):
        return RtsInstr()

    # --- Instructions: Header operations ------------------------------------
    def header_assign_instr(self, hdr_ref, value):
        res_value = value
        if isinstance(value, str):
            res_value = ipaddress.ip_address(value)
        return HeaderAssignInstr(header=str(hdr_ref), value=int(res_value))

    def hinc_instr(self, hdr_ref, value, reshdr_ref):
        return HeaderIncrementInstr(header=str(hdr_ref), value=int(value), reshdr=str(reshdr_ref))

    def paddtern_instr(self, *pattern):
        return PadToPatternInstr(pattern=pattern)

    def clone_instr(self, target):
        return CloneInstr(port=str(target))

    def activate_instr(self, target):
        return ActivateInstr(program=str(target))

    # --- Instructions: Conversion -------------------------------------------
    def copy_header_to_var_instr(self, header_ref, var_ref):
        return CopyHeaderToVarInstr(header=str(header_ref), var=str(var_ref))

    def copy_hash_to_var_instr(self, hash_ref, var_ref):
        return CopyHashToVarInstr(hash=str(hash_ref), var=str(var_ref))

    def copy_var_to_header_instr(self, var_ref, header_ref):
        return CopyVarToHeaderInstr(var=str(var_ref), header=str(header_ref))

    def random_instr(self, num_bits, var_ref):
        return RandomInstr(num_bits, var=str(var_ref))
    
    def time_instr(self, var_ref):
        return TimeInstr(resvar=str(var_ref))

    # --- Instructions: Memory ------------------------------------------------
    def mget_instr(self, *args):
        access_type="NEW"
        reg=args[0]
        index=args[1]
        var=args[2]
        if len(args) == 4:
            access_type=args[3]

        return MemoryGetInstr(reg, index, var, access_type)

    def mset_instr(self, reg, index, value):
        return MemorySetInstr(reg, index, value)

    def minc_instr(self, *args):
        access_type = "NEW"
        reg = args[0]
        index = args[1]
        increment = args[2]
        var = args[3]
        if len(args) == 5:
            access_type = args[4]

        return MemoryIncInstr(reg, index, increment, var, access_type)

    def conditional_clause(self, cond_expr, target_label):
        return BrCondInstr(cond=cond_expr, label=str(target_label))

    def jmp_instr(self, target_label):
        return JmpInstr(label=str(target_label))
    
    # --- Instructions: Arithmetic -------------------------------------------
    def sub_instr(self, lvar, rvar, resvar):
        return SubInstr(lvar, rvar, resvar)
    
    def sum_instr(self, lvar, rvar, resvar):
        return SumInstr(lvar, rvar, resvar)
    
    def mul_instr(self, lvar, value, resvar):
        return MulInstr(lvar, value, resvar)

    def inc_instr(self, lvar, value, resvar):
        return IncInstr(lvar, int(value), resvar)

    # --- Instructions: State -------------------------------------------------
    def in_instr(self, var_ref):
        return InInstr(var=str(var_ref))

    def out_instr(self, var_ref):
        return OutInstr(var=str(var_ref))

    # --- Instructions: Default actions --------------------------------------
    def default_fwd_instr(self, target):
        return FwdInstr(port=str(target))
    
    def default_fwd_queue_instr(self, target, qid):
        target_str = str(target)
        return FwdAndEnqueueInstr(qname=target_str, port=target_str, qid=int(qid))

    def default_drop_instr(self):
        return DropInstr()

    # --- Boolean expressions → canonical string ----------------------------
    def comparison(self, left, op, right):
        return BooleanExpression(left=str(left), op=str(op), right=right)

    def and_expr(self, left, right):
        return BooleanExpression(left=left, op="&&", right=right)

    def or_expr(self, left, right):
        return BooleanExpression(left=left, op="||", right=right)

    def not_expr(self, *args):
        # Ex: !expr  → args = ['!', <BooleanExpression>]
        if len(args) == 2 and str(args[0]) == "!":
            expr = args[1]
            return BooleanExpression(left=None, op="!", right=expr)

        # Ex: (expr) ou comparação direta → apenas devolve a expressão
        return args[-1]

    def comp_op(self, t):          return str(t.type)
    def arith_val(self, x):        return x
    def var_ref(self, name):       return TypedRef(str(name), "var_ref")

    def NEWLINE(self, t):
        return None

    # # --- Default
    # def __default__(self, data, children, meta):
    #     if len(children) == 1:
    #         return children[0]
    #     return children

    def __default__(self, data, children, meta):
        children = [c for c in children if c is not None]
        if len(children) == 1:
            return children[0]
        return children

def parse_stagerun_program(text: str) -> ProgramNode:
    tree = parser.parse(text)
    return StageRunTransformer().transform(tree)
