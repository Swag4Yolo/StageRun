# src/stagerun_compiler/ast_nodes.py
from dataclasses import dataclass

@dataclass
class PortDecl:
    name: str
    lineno: int

@dataclass
class ForwardInstr:
    dest: str
    lineno: int
