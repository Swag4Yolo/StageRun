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
    PADTTERN        = "PADTTERN"
    CLONE           = "CLONE"
    IF              = "IF"

    @classmethod
    def get_ISA_values(cls) -> List[str]:
        vals = []
        for val in cls:
            if val != ISA.VERSION:
                vals.append(val.value)
        return vals