from enum import Enum
from typing import List

class ISA(Enum):
    VERSION         = 1.3
    FWD             = "FWD"
    DROP            = "DROP"
    RTS             = "RTS"
    FWD_AND_ENQUEUE = "FWD_AND_ENQUEUE"
    HINC            = "HINC"
    HASSIGN         = "HASSIGN"
    HTOVAR          = "HTOVAR"
    HASHTOVAR       = "HASHTOVAR"
    VTOHEADER       = "VTOHEADER"
    RAND            = "RAND"
    TIME            = "TIME"
    MGET            = "MGET"
    MSET            = "MSET"
    MINC            = "MINC"
    BRCOND          = "BRCOND"
    JMP             = "JMP"
    SUB             = "SUB"
    SUM             = "SUM"
    MUL             = "MUL"
    INC             = "INC"
    PADTTERN        = "PADTTERN"
    CLONE           = "CLONE"
    ACTIVATE        = "ACTIVATE"
    IN              = "IN"
    OUT             = "OUT"
    IF              = "IF"

    @classmethod
    def get_ISA_values(cls) -> List[str]:
        vals = []
        for val in cls:
            if val != ISA.VERSION:
                vals.append(val.value)
        return vals
