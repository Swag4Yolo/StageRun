from lib.tofino.types import *
from lib.tofino.constants import *


class P1TableKeys(BaseTableKeys):
    def __init__(self, program_id=1, next_instruction=DISABLED, pkt_id=[DISABLED, DISABLED]):
        super().__init__()
        self.next_instruction = next_instruction
        self.pkt_id = pkt_id
        self.program_id = program_id

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["flow_md.next_instruction", self.next_instruction, "exact"],
            ["ig_md.pkt_filter_md.pkt_id", self.pkt_id[0], self.pkt_id[1], "ternary"],
            ["hdr.bridge_meta.program_id", self.program_id, "exact"]
        ]
    
    
    @classmethod
    def from_key_dict(cls, key_dict):
        print("Key_dict")
        print(key_dict)
        return cls(
            next_instruction=
                int(key_dict['flow_md.next_instruction']['value']),
                # key_dict['flow_md.next_instruction']['mask']
            pkt_id=[
                int(key_dict['ig_md.pkt_filter_md.pkt_id']['value']),
                int(key_dict['ig_md.pkt_filter_md.pkt_id']['mask'])
            ],
            program_id=int(key_dict['hdr.bridge_meta.program_id']['value'])
        )

        
class P2TableKeys(BaseTableKeys):

    def __init__(self, program_id=1, next_instruction=DISABLED, pkt_id=[DISABLED, DISABLED], cond_mode=[DISABLED, DISABLED], cond_val=[DISABLED, DISABLED], cond_mode_2=[DISABLED, DISABLED], cond_val_2=[DISABLED, DISABLED]):
        super().__init__()
        self.program_id = program_id
        self.next_instruction = next_instruction
        self.pkt_id = pkt_id
        self.cond_mode = cond_mode
        self.cond_val = cond_val
        self.cond_mode_2 = cond_mode_2
        self.cond_val_2 = cond_val_2

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["hdr.bridge_meta.program_id", self.program_id, "exact"],
            ["flow_md.next_instruction", self.next_instruction, "exact"],
            ["ig_md.pkt_filter_md.pkt_id", self.pkt_id[0], self.pkt_id[1], "ternary"],

            ["res_md.cond_md.cond_mode", self.cond_mode[0], self.cond_mode[1], "ternary"],
            ["res_md.cond_md.cond_val", self.cond_val[0], self.cond_val[1], "ternary"],
            ["res_md.cond_md.cond_mode_2", self.cond_mode_2[0], self.cond_mode_2[1], "ternary"],
            ["res_md.cond_md.cond_val_2", self.cond_val_2[0], self.cond_val_2[1], "ternary"],

        ]
    
    @classmethod
    def from_key_dict(cls, key_dict):
        return cls(
            next_instruction=
            # [
                key_dict['flow_md.next_instruction']['value'],
            #     key_dict['flow_md.next_instruction']['mask']
            # ],
            pkt_id=[
                key_dict['ig_md.pkt_filter_md.pkt_id']['value'],
                key_dict['ig_md.pkt_filter_md.pkt_id']['mask']
            ],
            cond_mode=[
                key_dict['res_md.cond_md.cond_mode']['value'],
                key_dict['res_md.cond_md.cond_mode']['mask']
            ],
            cond_val=[
                key_dict['res_md.cond_md.cond_val']['value'],
                key_dict['res_md.cond_md.cond_val']['mask']
            ],
            cond_mode_2=[
                key_dict['res_md.cond_md.cond_mode_2']['value'],
                key_dict['res_md.cond_md.cond_mode_2']['mask']
            ],
            cond_val_2=[
                key_dict['res_md.cond_md.cond_val_2']['value'],
                key_dict['res_md.cond_md.cond_val_2']['mask']
            ],
            program_id=key_dict['hdr.bridge_meta.program_id']['value']
        )

        
class SpeculativeKeys(BaseTableKeys):
    def __init__(self, program_id=1,next_instruction_speculative=DISABLED, pkt_id=[DISABLED, DISABLED], cond_mode=[DISABLED, DISABLED], cond_val=[DISABLED, DISABLED], cond_mode_2=[DISABLED, DISABLED], cond_val_2=[DISABLED, DISABLED]):
        super().__init__()
        self.program_id = program_id
        self.next_instruction_speculative = next_instruction_speculative
        self.pkt_id = pkt_id
        self.cond_mode = cond_mode
        self.cond_val = cond_val
        self.cond_mode_2 = cond_mode_2
        self.cond_val_2 = cond_val_2

    def to_key_list(self):
        return [
            ["flow_md.next_instruction_speculative", self.next_instruction_speculative, "exact"],
            ["ig_md.pkt_filter_md.pkt_id", self.pkt_id[0], self.pkt_id[1], "ternary"],

            ["res_md.cond_md.cond_mode", self.cond_mode[0], self.cond_mode[1], "ternary"],
            ["res_md.cond_md.cond_val", self.cond_val[0], self.cond_val[1], "ternary"],
            ["res_md.cond_md.cond_mode_2", self.cond_mode_2[0], self.cond_mode_2[1], "ternary"],
            ["res_md.cond_md.cond_val_2", self.cond_val_2[0], self.cond_val_2[1], "ternary"],
            ["hdr.bridge_meta.program_id", self.program_id, "exact"],

        ]
        
    @classmethod
    def from_key_dict(cls, key_dict):
        return cls(
            next_instruction=
            # [
                key_dict['flow_md.next_instruction_speculative']['value'],
            #     key_dict['flow_md.next_instruction_speculative']['mask']
            # ],
            pkt_id=[
                key_dict['ig_md.pkt_filter_md.pkt_id']['value'],
                key_dict['ig_md.pkt_filter_md.pkt_id']['mask']
            ],
            cond_mode=[
                key_dict['res_md.cond_md.cond_mode']['value'],
                key_dict['res_md.cond_md.cond_mode']['mask']
            ],
            cond_val=[
                key_dict['res_md.cond_md.cond_val']['value'],
                key_dict['res_md.cond_md.cond_val']['mask']
            ],
            cond_mode_2=[
                key_dict['res_md.cond_md.cond_mode_2']['value'],
                key_dict['res_md.cond_md.cond_mode_2']['mask']
            ],
            cond_val_2=[
                key_dict['res_md.cond_md.cond_val_2']['value'],
                key_dict['res_md.cond_md.cond_val_2']['mask']
            ],
            program_id=key_dict['hdr.bridge_meta.program_id']['value']
        )
