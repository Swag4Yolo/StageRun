from lib.tofino.types import *
from lib.tofino.constants import *

class WritePhaseConditionalMechanismAfterRegKeys(BaseTableKeys):
    def __init__(self, next_instruction=DISABLED, pkt_id=DISABLED):
        super().__init__()
        self.next_instruction = next_instruction
        self.pkt_id = pkt_id

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"]]
        return [
            ["hdr.bridge_meta.f1.next_instruction",     self.next_instruction,  "exact"],
            ["ig_md.pkt_filter_md.pkt_id",              self.pkt_id,            "exact"],
        ]
        
class WritePhaseConditionalMechanismAfterReg(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.process_conditional_after_reg_f1_t")
    
    # Action implementations
    def process_conditional_after_reg_f1(self, ni=DISABLED,pkt_id=DISABLED, cond_mode=DISABLED, cond_val=DISABLED, cond_mode_2=DISABLED, cond_val_2=DISABLED):
        keys = WritePhaseConditionalMechanismAfterRegKeys(ni, pkt_id)
        action = BaseAction("process_conditional_after_reg_f1", cond_mode, cond_val, cond_mode_2, cond_val_2)
        self.add_entry(keys, action)