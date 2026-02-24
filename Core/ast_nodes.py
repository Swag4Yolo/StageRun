from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ======================
# Base AST nodes
# ======================
class TypedRef(str):
    """
    String-like reference carrying internal type metadata.
    It serializes as a plain string in JSON.
    """
    __slots__ = ("ref_kind",)

    def __new__(cls, value: str, ref_kind: str):
        obj = str.__new__(cls, value)
        obj.ref_kind = ref_kind
        return obj

    def __reduce__(self):
        return (TypedRef, (str(self), self.ref_kind))


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
    port: str
    type: str
    size: int


@dataclass
class SetupDecl(ASTNode):
    """Base type for control-plane setup declarations."""
    pass


@dataclass
class LoopSetupDecl(SetupDecl):
    """setup loop <out_port> <in_port>"""
    out_port: str
    in_port: str


@dataclass
class PatternSetupDecl(SetupDecl):
    """setup pattern <name> <size>..."""
    name: str
    pattern: List[int]


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
    """<name>: (parse-level label declaration)"""
    name: str


@dataclass
class HashDecl(ASTNode):
    """HASH <name> { ... }"""
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
    port: str


@dataclass
class DropInstr(InstructionNode):
    pass


@dataclass
class RtsInstr(InstructionNode):
    pass


@dataclass
class FwdAndEnqueueInstr(InstructionNode):
    qname: str
    port: str
    qid: int


@dataclass
class HeaderIncrementInstr(InstructionNode):
    header: str
    value: int
    reshdr: str


@dataclass
class HeaderAssignInstr(InstructionNode):
    header: str
    value: int


@dataclass
class CopyHeaderToVarInstr(InstructionNode):
    header: str
    var: str


@dataclass
class CopyHashToVarInstr(InstructionNode):
    hash: str
    var: str


@dataclass
class CopyVarToHeaderInstr(InstructionNode):
    var: str
    header: str


@dataclass
class PadToPatternInstr(InstructionNode):
    pattern: List[int]


@dataclass
class CloneInstr(InstructionNode):
    port: str

@dataclass
class ActivateInstr(InstructionNode):
    program: str

@dataclass
class RandomInstr(InstructionNode):
    num_bits: int
    var: str

@dataclass
class TimeInstr(InstructionNode):
    resvar: str

@dataclass
class InInstr(InstructionNode):
    var: str

@dataclass
class OutInstr(InstructionNode):
    var: str

@dataclass
class MemoryGetInstr(InstructionNode):
    reg: str
    index: str
    var: str
    acess_type: str


@dataclass
class MemorySetInstr(InstructionNode):
    reg: str
    index: str
    value: str | int


@dataclass
class MemoryIncInstr(InstructionNode):
    reg: str
    index: str
    increment: str | int
    var: str
    acess_type: str


# ======================
# Arithmetics
# ======================
@dataclass
class SubInstr(InstructionNode):
    lvar: str
    rvar: str
    resvar: str

@dataclass
class SumInstr(InstructionNode):
    lvar: str
    rvar: str
    resvar: str

@dataclass
class MulInstr(InstructionNode):
    lvar: str
    value: int
    resvar: str

@dataclass
class IncInstr(InstructionNode):
    lvar: str
    value: int
    resvar: str


# ======================
# Conditionals
# ======================

@dataclass
class BrCondInstr(InstructionNode):
    """ .br.cond <bool_expr>, <label> """
    cond: BooleanExpression
    label: str

@dataclass
class JmpInstr(InstructionNode):
    """ .jmp <label> """
    label: str

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
# Handler (with labels / blocks)
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
class HandlerPosKey(ASTNode):
    field: str
    operand: str
    value: str | int


@dataclass
class HandlerPosDefault(ASTNode):
    instr: InstructionNode


@dataclass
class HandlerPosClause(ASTNode):
    key: HandlerPosKey
    default_action: InstructionNode


@dataclass
class BasicBlockNode(ASTNode):
    """
    A labeled basic block inside a handler body.
    The implicit entry block should use label="entry".
    """
    label: str
    instructions: List[InstructionNode] = field(default_factory=list)


@dataclass
class HandlerBodyNode(ASTNode):
    """
    Handler body is a list of basic blocks.
    The first block is the entry block.
    """
    blocks: List[BasicBlockNode] = field(default_factory=list)


@dataclass
class HandlerNode(ASTNode):
    name: str
    keys: List[HandlerKey] = field(default_factory=list)
    default_action: Optional[InstructionNode] = None
    pos_clauses: List[HandlerPosClause] = field(default_factory=list)
    body: Optional[HandlerBodyNode] = None


# ======================
# Program root
# ======================

@dataclass
class ProgramNode(ASTNode):
    ports_in: List[PortDecl] = field(default_factory=list)
    ports_out: List[PortDecl] = field(default_factory=list)
    queues: List[QueueSetDecl] = field(default_factory=list)
    setups: List[SetupDecl] = field(default_factory=list)
    vars: List[VarDecl] = field(default_factory=list)
    regs: List[RegDecl] = field(default_factory=list)
    hashes: List[HashDecl] = field(default_factory=list)
    handlers: List[HandlerNode] = field(default_factory=list)
