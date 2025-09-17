from lib.tofino.types import *
from lib.tofino.constants import *

class RandomKeys(BaseTableKeys):
    """
    Represents the keys for the Random Table presented in the initblock.
    Provides a structured way to define key values with IntelliSense support.
    """
    def __init__(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        super().__init__()

        self.f1_next_instr = f1_next_instr
        self.f2_next_instr = f2_next_instr
        self.ingress_port = ingress_port
        self.original_ingress_port = original_ingress_port
        self.program_id = program_id

    @classmethod
    def from_key_dict(cls, key_dict):
        return cls(
            f1_next_instr=[
                key_dict['hdr.bridge_meta.f1.next_instruction']['value'],
                key_dict['hdr.bridge_meta.f1.next_instruction']['mask']
            ],
            f2_next_instr=[
                key_dict['hdr.bridge_meta.f2.next_instruction']['value'],
                key_dict['hdr.bridge_meta.f2.next_instruction']['mask']
            ],
            ingress_port=[
                key_dict['ig_intr_md.ingress_port']['value'],
                key_dict['ig_intr_md.ingress_port']['mask']
            ],
            original_ingress_port=[
                key_dict['hdr.bridge_meta.original_ingress_port']['value'],
                key_dict['hdr.bridge_meta.original_ingress_port']['mask']
            ],
            program_id=key_dict['hdr.bridge_meta.program_id']['value']
        )
    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"]]
        return [
            ["hdr.bridge_meta.f1.next_instruction", self.f1_next_instr[0], self.f1_next_instr[1] ,  "ternary"],
            ["hdr.bridge_meta.f2.next_instruction", self.f2_next_instr[0], self.f2_next_instr[1] ,  "ternary"],
            ["ig_intr_md.ingress_port", self.ingress_port[0], self.ingress_port[1] ,                "ternary"],
            ["hdr.bridge_meta.original_ingress_port", self.original_ingress_port[0], self.original_ingress_port[1] ,"ternary"],
            ["hdr.bridge_meta.program_id", self.program_id,                                         "exact"],
        ]
        
class RandomMechanism(BaseTable):
    """
    Represents the Random Mechanism presented in the initblock
    """

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.initblock.random_t")
    
    #TODO: for now the program puts the random variable always in the beginning of the program without keys; later if needed we add the keys
    def random_32b_v1(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_32b_v1")
        self.add_entry(keys, action)
    
    def random_32b_v2(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_32b_v2")
        self.add_entry(keys, action)
    
    def random_32b_v3(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_32b_v3")
        self.add_entry(keys, action)
    
    def random_32b_v4(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_32b_v4")
        self.add_entry(keys, action)
    
    def random_4b_v1(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_4b_v1")
        self.add_entry(keys, action)
    
    def random_4b_v2(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_4b_v2")
        self.add_entry(keys, action)
    
    def random_4b_v3(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_4b_v3")
        self.add_entry(keys, action)
    
    def random_4b_v4(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("random_4b_v4")
        self.add_entry(keys, action)

    def get_timestamp_v1(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("get_timestamp_v1")
        self.add_entry(keys, action)

    def get_timestamp_v2(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("get_timestamp_v2")
        self.add_entry(keys, action)

    def get_timestamp_v3(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("get_timestamp_v3")
        self.add_entry(keys, action)

    def get_timestamp_v4(self, f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], program_id=1):
        keys = RandomKeys(f1_next_instr, f2_next_instr, ingress_port, original_ingress_port, program_id)
        action = BaseAction("get_timestamp_v4")
        self.add_entry(keys, action)

    def remove_entries_for_pid(self, pid):
        # Obter todas as entradas instaladas na pre_filter
        table_keys = self.get_all_entries(False)

        for _, key in table_keys:
            key_dict = key.to_dict()
            key_pid = key_dict['hdr.bridge_meta.program_id']['value']

            # Se o program_id for o mesmo, remove entrada
            if key_pid == pid:
                keys = RandomKeys.from_key_dict(key_dict)
                self.delete_entry(keys)