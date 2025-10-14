# src/stagerun_compiler/ast_nodes.py
from dataclasses import dataclass
from typing import List, Optional, Union

@dataclass
class PortDecl:
    name: str
    lineno: int

@dataclass
class ForwardInstr:
    dest: str
    lineno: int

@dataclass
class HeaderIncrementInstruction:
    target: str      # e.g. "IPV4.TTL"
    value: int       # positive or negative
    lineno: int

@dataclass
class KeyCondition:
    field: str       # e.g. "PKT.PORT" or "IPV4.DST"
    op: str          # e.g. "=="
    value: str       # e.g. "ExternalPort" or "10.0.0.0/24" (strings stored without quotes)
    lineno: int

@dataclass
class PreFilter:
    name: str
    keys: List[KeyCondition]
    default: Optional[Union[ForwardInstr, str]]  # ForwardInstr or "DROP" or None
    body: List[Union[ForwardInstr, HeaderIncrementInstruction]]
    lineno: int
