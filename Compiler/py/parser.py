# src/stagerun_compiler/parser.py
from lark import Lark, Transformer, v_args
from ast_nodes import (
    PortDecl,
    ForwardInstr,
    HeaderIncrementInstruction,
    KeyCondition,
    PreFilter,
)

GRAMMAR = r"""
start: statement*
statement: port_decl | prefilter

port_decl: "PORT" NAME                         -> port_decl

prefilter: "PREFILTER" NAME prefilter_body "END"   -> prefilter
prefilter_body: (key_clause | default_clause | body_clause)*

key_clause: "KEY" header_operand "==" value        -> key_clause
default_clause: "DEFAULT" default_action           -> default_clause
body_clause: "BODY" instr_list "END"               -> body_clause

instr_list: instr*                                -> instr_list

default_action: "FWD" NAME                         -> default_fwd
              | "DROP"                            -> default_drop

instr: fwd_instr
     | hinc_instr

fwd_instr: "FWD" NAME                               -> fwd_instr
hinc_instr: "HINC" header_operand SIGNED_NUMBER     -> hinc_instr

header_operand: NAME "." NAME                       -> header_operand
value: ESCAPED_STRING | NAME                        -> value

NAME: /[A-Za-z_][A-Za-z0-9_]*/
%import common.ESCAPED_STRING
%import common.SIGNED_NUMBER
%import common.WS_INLINE
%ignore WS_INLINE
%ignore /#[^\n]*/   // comments
%ignore /[\r\n]+/   // newlines
"""

# -----------------------------------------------------------------------------
# Transformer: produce AST nodes only (no intermediary dicts/Tree leaking)
# -----------------------------------------------------------------------------
@v_args(meta=True)
class SRTransformer(Transformer):
    def start(self, meta, children):
        # children: list of PortDecl | PreFilter
        return children

    def statement(self, meta, children):
        return children[0]

    # ----------------- Port -----------------
    def port_decl(self, meta, children):
        # children[0] is a Token NAME
        return PortDecl(name=str(children[0].value), lineno=meta.line)

    # ----------------- Prefilter -----------------
    def prefilter(self, meta, children):
        # children[0] is NAME token
        name = str(children[0].value)
        clauses = children[1:] if len(children) > 1 else []

        keys = []
        default = None
        body = []

        default_seen = False

        for c in clauses:
            # key_clause returns KeyCondition
            if isinstance(c, KeyCondition):
                keys.append(c)
            # default_clause returns either ForwardInstr or the string "DROP"
            elif isinstance(c, ForwardInstr) or (isinstance(c, str) and c == "DROP"):
                if default_seen:
                    # multiple DEFAULT clauses => syntax error
                    raise SyntaxError(f"Multiple DEFAULT clauses in PREFILTER '{name}' (line {meta.line})")
                default_seen = True
                default = c
            # body_clause returns list of instr (may be empty)
            elif isinstance(c, list):
                body = c
            else:
                # Shouldn't happen — defensive
                raise SyntaxError(f"Unexpected clause in PREFILTER '{name}' at line {meta.line}: {type(c)}")

        # ensure lists are present (possibly empty)
        keys = list(keys)
        body = list(body)

        return PreFilter(name=name, keys=keys, default=default, body=body, lineno=meta.line)

    def key_clause(self, meta, children):
        # children: [header_operand (str "NAME.FIELD"), value (str)]
        field = children[0]        # str "NAME.FIELD"
        value = children[1]        # str (no quotes if was string)
        return KeyCondition(field=field, op="==", value=value, lineno=meta.line)

    def default_clause(self, meta, children):
        # children[0] is default_action result (ForwardInstr or "DROP")
        node = children[0]
        # set correct lineno on node if ForwardInstr
        if isinstance(node, ForwardInstr):
            node.lineno = meta.line
        return node

    def body_clause(self, meta, children):
        # children[0] is instr_list -> a list of AST instrs
        return children[0]

    def instr_list(self, meta, children):
        # children is a list of instr nodes (possibly empty)
        return children

    def default_fwd(self, meta, children):
        # children[0] is NAME token
        return ForwardInstr(dest=str(children[0].value), lineno=meta.line)

    def default_drop(self, meta, children):
        return "DROP"

    # ----------------- Instructions -----------------
    def fwd_instr(self, meta, children):
        return ForwardInstr(dest=str(children[0].value), lineno=meta.line)

    def hinc_instr(self, meta, children):
        target = children[0]   # header_operand -> str like "IPV4.TTL"
        value = int(children[1])
        return HeaderIncrementInstruction(target=target, value=value, lineno=meta.line)

    # ----------------- Operands / values -----------------
    def header_operand(self, meta, children):
        # children are tokens NAME and NAME
        left = str(children[0].value)
        right = str(children[1].value)
        return f"{left}.{right}"

    def value(self, meta, children):
        token = children[0]
        # ESCAPED_STRING tokens have quotes in .value -> strip them
        val = str(token.value)
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        return val

# -----------------------------------------------------------------------------
parser = Lark(GRAMMAR, parser="lalr", propagate_positions=True)
transformer = SRTransformer()

def parse_program(text: str):
    """
    Parse StageRun source text into a list of AST nodes:
      - PortDecl
      - PreFilter

    Each PreFilter keys/default/body are AST nodes (no dicts/Tree leftovers).
    """
    tree = parser.parse(text)
    return transformer.transform(tree)

