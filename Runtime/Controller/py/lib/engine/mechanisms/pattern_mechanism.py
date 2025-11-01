from lib.tofino.types import *
from lib.tofino.constants import *

class PatternKeys(BaseTableKeys):
    def __init__(self, program_id=1, pkt_cntr=[DISABLED, DISABLED], total_len=[DISABLED,DISABLED]):
        super().__init__()
        self.program_id = program_id
        self.pkt_cntr = pkt_cntr
        self.total_len = total_len

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        return [
            ["hdr.bridge_meta.program_id", self.program_id,                              "exact"],
            ["hdr.bridge_meta.pkt_cntr",   self.pkt_cntr[0],     self.pkt_cntr[1],       "ternary"],
            ["hdr.ipv4.totalLen",          self.total_len[0],    self.total_len[1],      "range"],
        ]
        
class PatternMechanism(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.pattern_block.pattern_t")
    
    # Action implementations
    def add_size_pattern(self, program_id:int, pattern:list):
        
        def __add_pattern__(name, pattern_val_1, pattern_val_2):
            return BaseAction(name, pattern_val_1, pattern_val_2)

        sorted_pattern = sorted(pattern) 

        ### Exact matches of the pattern
        for current_pattern in sorted_pattern:
            keys = PatternKeys(program_id=program_id, total_len=[current_pattern, current_pattern])
            action = __add_pattern__("pattern_res", current_pattern, current_pattern)
            self.add_entry(keys, action)

        ### Less than the Pattern [...]
        prev_pattern_key = 0
        for current_pattern in sorted_pattern: # [200, 500]
            current_pattern_key = current_pattern - SHARED_META_SIZE

            #TODO: check if current pattern is less than < Shared Meta Size is not possible

            keys = PatternKeys(total_len=[prev_pattern_key, current_pattern_key])
            action = __add_pattern__("pattern_res", current_pattern, current_pattern)
            self.add_entry(keys, action)

            prev_pattern_key = current_pattern_key

    