# src/stagerun_compiler/parser.py
from lark import Lark, Transformer, v_args
from ast_nodes import *

GRAMMAR = r"""
start: statement*
statement: port_decl | instr

// data declarations
port_decl: "PORT" NAME           -> port_decl

// instructions
instr: fwd_instr
     | hinc_instr

fwd_instr: "FWD" NAME            -> fwd_instr
hinc_instr: "HINC" header_operand SIGNED_NUMBER -> hinc_instr

// operands
header_operand: NAME "." NAME     -> header_operand

NAME: /[A-Za-z_][A-Za-z0-9_]*/

%import common.SIGNED_NUMBER
%import common.WS_INLINE
%ignore WS_INLINE
%ignore /#[^\n]*/   // comments
%ignore /[\r\n]+/  // ignore newlines
"""

@v_args(meta=True)
class SRTransformer(Transformer):
    def start(self, meta, children):
        return children

    def statement(self, meta, children):
        # devolve só o nó AST dentro do statement
        return children[0]

    def instr(self, meta, children):
        # idem para instr
        return children[0]

    def port_decl(self, meta, children):
        name = str(children[0].value)
        return PortDecl(name=name, lineno=meta.line)

    def fwd_instr(self, meta, children):
        name = str(children[0].value)
        return ForwardInstr(dest=name, lineno=meta.line)

    def hinc_instr(self, meta, children):
        target = children[0]   # from header_operand
        value = int(children[1])
        return HeaderIncrementInstruction(
            target=target,
            value=value,
            lineno=meta.line
        )

    def header_operand(self, meta, children):
        # NAME "." NAME -> e.g., IPV4.TTL
        return f"{children[0].value}.{children[1].value}"

    # def var_operand(self, meta, children):
    #     return (children[0].value, None, False)
    

# Parser instance (LALR)
parser = Lark(GRAMMAR, parser="lalr", propagate_positions=True)
transformer = SRTransformer()

def parse_program(text: str):
    """
    Parse StageRun source text into a list of AST nodes (PortDecl, ForwardInstr).
    Raises lark exceptions if syntax invalid.
    """
    tree = parser.parse(text)
    ast = transformer.transform(tree)
    return ast
