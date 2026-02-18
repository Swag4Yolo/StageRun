# to use future references (BooleanExpression)
from __future__ import annotations 
from dataclasses import dataclass, field
from typing import List, Optional


# ======================
# Base AST nodes
# ======================

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


# ======================
# Declarations
# ======================

@dataclass
class PortDecl(ASTNode):
    """PIN/POUT declaration."""
    direction: str   # "IN" | "OUT"
    name: str
    qset: str


@dataclass
class QueueSetDecl(ASTNode):
    """QSET <queue_name> <type> <size>."""
    name: str
    type: str
    size: int


@dataclass
class VarDecl(ASTNode):
    """VAR <name>."""
    name: str

@dataclass
class RegDecl(ASTNode):
    """REG <name>."""
    name: str

@dataclass
class LabelDecl(ASTNode):
    """<name>:"""
    name: str

@dataclass
class HashDecl(ASTNode):
    """Hash <name>"""
    name: str
    args: List


# ======================
# Instructions
# ======================

@dataclass
class InstructionNode(ASTNode):
    """Base class for instructions."""
    pass


@dataclass
class FwdInstr(InstructionNode):
    port: str  # port name

@dataclass
class DropInstr(InstructionNode):
    pass


@dataclass
class FwdAndEnqueueInstr(InstructionNode):
    port: str
    qid: int


@dataclass
class HeaderIncrementInstr(InstructionNode):
    """HINC IPV4.TTL <value>."""
    header: str         # e.g., "IPV4.TTL"
    value: int


@dataclass
class HeaderAssignInstr(InstructionNode):
    """HASSIGN IPV4.ID <value>."""
    header: str         # e.g., "IPV4.ID"
    value: int


@dataclass
class CopyHeaderToVarInstr(InstructionNode):
    """.copy IPV4.PROTO, $proto"""
    header: str         # e.g., "IPV4.PROTO"
    var: str

@dataclass
class CopyHashToVarInstr(InstructionNode):
    """.hashcopy hash_name, $value"""
    hash: str         # e.g., "IPV4.PROTO"
    var: str

@dataclass
class CopyVarToHeaderInstr(InstructionNode):
    """.hcopy $proto, IPV4.TCP"""
    var: str         # e.g., "IPV4.PROTO"
    header: str

@dataclass
class PadToPatternInstr(InstructionNode):
    """HTOVAR IPV4.PROTO -> proto."""
    pattern: List[int]        

@dataclass
class CloneInstr(InstructionNode):
    """CLONE P1_OUT"""
    port: str  

# ======================
# Conditionals
# ======================

@dataclass
class BooleanExpression(ASTNode):
    left: str | BooleanExpression | None
    op: str
    right: str | BooleanExpression | None



@dataclass
class ConditionBlock(ASTNode):
    condition: BooleanExpression
    body: List[InstructionNode]


@dataclass
class IfNode(InstructionNode):
    branches: List[ConditionBlock] = field(default_factory=list)
    else_body: Optional[List[InstructionNode]] = None


# ======================
# Handler
# ======================

@dataclass
class HandlerKey(ASTNode):
    field: str
    operand: str
    value: str | int

@dataclass
class HandlerDefault(ASTNode):
    instr: InstructionNode

@dataclass
class HandlerBodyNode(ASTNode):
    instructions: List[InstructionNode] = field(default_factory=list)


@dataclass
class HandlerNode(ASTNode):
    name: str
    keys: List[HandlerKey] = field(default_factory=list)
    default_action: Optional[InstructionNode] = None
    body: Optional[HandlerBodyNode] = None


# ======================
# Program root
# ======================

@dataclass
class ProgramNode(ASTNode):
    ports_in: List[PortDecl] = field(default_factory=list)
    ports_out: List[PortDecl] = field(default_factory=list)
    qsets: List[QueueSetDecl] = field(default_factory=list)
    vars: List[VarDecl] = field(default_factory=list)
    regs: List[RegDecl] = field(default_factory=list)
    hashes: List[HashDecl] = field(default_factory=list)
    prefilters: List[HandlerNode] = field(default_factory=list)
