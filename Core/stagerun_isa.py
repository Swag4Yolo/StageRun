from enum import Enum
from typing import List

class ISA(Enum):
    VERSION         = 1.3
    FWD             = "FWD"
    DROP            = "DROP"
    FWD_AND_ENQUEUE = "FWD_AND_ENQUEUE"
    HINC            = "HINC"
    HASSIGN         = "HASSIGN"
    HTOVAR          = "HTOVAR"
    HASHTOVAR       = "HASHTOVAR"
    VTOHEADER       = "VTOHEADER"
    RAND            = "RAND"
    MGET            = "MGET"
    MSET            = "MSET"
    MINC            = "MINC"
    BRCOND          = "BRCOND"
    SUB             = "SUB"
    SUM             = "SUM"
    MUL             = "MUL"
    PADTTERN        = "PADTTERN"
    CLONE           = "CLONE"
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
