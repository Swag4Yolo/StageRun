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
    """QSET <queue_name> <port> <size>."""
    name: str
    port: str
    size: int


@dataclass
class VarDecl(ASTNode):
    """VAR <name>."""
    name: str

@dataclass
class RegDecl(ASTNode):
    """REG <name>."""
    name: str


# ======================
# Instructions
# ======================

@dataclass
class InstructionNode(ASTNode):
    """Base class for instructions."""
    pass


@dataclass
class ForwardInstr(InstructionNode):
    target: str  # port name

@dataclass
class DropInstruction(InstructionNode):
    pass


@dataclass
class ForwardAndEnqueueInstr(InstructionNode):
    target: str
    qid: int


@dataclass
class HeaderIncrementInstruction(InstructionNode):
    """HINC IPV4.TTL <value>."""
    target: str         # e.g., "IPV4.TTL"
    value: int


@dataclass
class AssignmentInstruction(InstructionNode):
    """ASSIGN IPV4.ID <value>."""
    target: str         # e.g., "IPV4.ID"
    value: int


@dataclass
class HtoVarInstr(InstructionNode):
    """HTOVAR IPV4.PROTO -> proto."""
    target: str         # e.g., "IPV4.PROTO"
    var_name: str

@dataclass
class PadToPatternInstr(InstructionNode):
    """HTOVAR IPV4.PROTO -> proto."""
    pattern: List[int]        

@dataclass
class CloneInstr(InstructionNode):
    """CLONE P1_OUT"""
    target: str  

# ======================
# Conditionals
# ======================

@dataclass
class BooleanExpression(ASTNode):
    """Boolean expression represented as canonical string (no tokens/trees)."""
    text: str


@dataclass
class ConditionBlock(ASTNode):
    condition: BooleanExpression
    body: List[InstructionNode]


@dataclass
class IfNode(InstructionNode):
    branches: List[ConditionBlock] = field(default_factory=list)
    else_body: Optional[List[InstructionNode]] = None


# ======================
# Prefilter
# ======================

@dataclass
class PreFilterKey(ASTNode):
    field: str
    operand: str
    value: str


@dataclass
class PreFilterDefault(ASTNode):
    instr: InstructionNode

@dataclass
class PreFilterDefault(ASTNode):
    instr: InstructionNode

@dataclass
class BodyNode(ASTNode):
    instructions: List[InstructionNode] = field(default_factory=list)


@dataclass
class PreFilterNode(ASTNode):
    name: str
    keys: List[PreFilterKey] = field(default_factory=list)
    default_action: Optional[InstructionNode] = None
    body: Optional[BodyNode] = None


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
    prefilters: List[PreFilterNode] = field(default_factory=list)
