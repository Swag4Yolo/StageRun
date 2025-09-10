from lib.tofino.types import *
from lib.tofino.constants import *

class WritePhaseConditionalMechanismAfterRegKeys(BaseTableKeys):
    def __init__(self, program_id=1, next_instruction=DISABLED, pkt_id=DISABLED):
        super().__init__()
        self.program_id = program_id
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
            ["hdr.bridge_meta.program_id", self.program_id, "exact"],

        ]
        
    @classmethod
    def from_key_dict(cls, key_dict):
        return cls(
            program_id=key_dict['hdr.bridge_meta.program_id']['value'],
            next_instruction=key_dict['hdr.bridge_meta.f1.next_instruction']['value'],
            pkt_id=key_dict['ig_md.pkt_filter_md.pkt_id']['value']
        )


class WritePhaseConditionalMechanismAfterReg(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.process_conditional_after_reg_f1_t")
    
    # Action implementations
    def process_conditional_after_reg_f1(self, program_id=1, ni=DISABLED,pkt_id=DISABLED, cond_mode=DISABLED, cond_val=DISABLED, cond_mode_2=DISABLED, cond_val_2=DISABLED):
        keys = WritePhaseConditionalMechanismAfterRegKeys(program_id, ni, pkt_id)
        action = BaseAction("process_conditional_after_reg_f1", cond_mode, cond_val, cond_mode_2, cond_val_2)
        self.add_entry(keys, action)

    def remove_entries_for_pid(self, pid):
        # Obter todas as entradas instaladas na pre_filter
        table_keys = self.get_all_entries(False)

        for _, key in table_keys:
            key_dict = key.to_dict()
            key_pid = key_dict['hdr.bridge_meta.program_id']['value']

            # Se o program_id for o mesmo, remove entrada
            if key_pid == pid:
                keys = WritePhaseConditionalMechanismAfterRegKeys.from_key_dict(key_dict)
                self.delete_entry(keys)