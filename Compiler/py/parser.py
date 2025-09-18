# src/stagerun_compiler/parser.py
from lark import Lark, Transformer, v_args
from ast_nodes import PortDecl, ForwardInstr

GRAMMAR = r"""
start: statement*
statement: port_decl | instr

// data declarations
port_decl: "PORT" NAME           -> port_decl

// instructions
instr: "FWD" NAME                -> fwd_instr

NAME: /[A-Za-z_][A-Za-z0-9_]*/

%import common.WS_INLINE
%ignore WS_INLINE
%ignore /#[^\n]*/   // comments
%ignore /[\r\n]+/  // ignore newlines (we want to support line breaks)
"""

@v_args(meta=True)
class SRTransformer(Transformer):
    def start(self, meta, children):
        return children

    def port_decl(self, meta, children):
        name = str(children[0].value)
        return PortDecl(name=name, lineno=meta.line)

    def fwd_instr(self, meta, children):
        name = str(children[0].value)
        return ForwardInstr(dest=name, lineno=meta.line)


# Parser instance (LALR)
parser = Lark(GRAMMAR, parser="lalr", propagate_positions=True)
transformer = SRTransformer()

def parse_program(text: str):
    """
    Parse StageRun source text into a list of AST nodes (PortDecl, ForwardInstr).
    Raises lark exceptions if syntax invalid.
    """
    ast = []
    tree = parser.parse(text)
    lark_trees = transformer.transform(tree)
    # Lark parser produces a Tree with a root rule and children nodes.
    for tree in lark_trees:
        ast.extend(tree.children)
    return ast
