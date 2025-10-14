from dataclasses import dataclass, field
from typing import List, Optional
from lark import ast_utils

# Base class for AST nodes
class _Ast(ast_utils.Ast):
    pass

@dataclass
class PortDecl(_Ast):
    name: str

# Instructions
@dataclass
class ForwardInstr(_Ast):
    dest: str

@dataclass
class HeaderIncrementInstruction(_Ast):
    target: str      
    value: int

@dataclass
class DropInstr(_Ast):
    pass

# Prefilter clauses
@dataclass
class KeyClause(_Ast):
    field: str       
    value: str      

@dataclass
class DefaultClause(_Ast):
    action: _Ast     

@dataclass
class BodyClause(_Ast):
    statements: List[_Ast] = field(default_factory=list)

@dataclass
class PreFilter(_Ast):
    name: str
    keys: List[KeyClause] = field(default_factory=list)
    default: Optional[DefaultClause] = None
    body: Optional[BodyClause] = None
