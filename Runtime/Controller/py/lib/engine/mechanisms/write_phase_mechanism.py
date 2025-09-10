from lib.tofino.types import *
from lib.tofino.constants import *
     

class WritePhaseKeys(BaseTableKeys):
    def __init__(self, program_id=1):
        
        super().__init__()
        self.program_id         = program_id

    @classmethod
    def from_key_dict(cls, key_dict):
        return cls(
            program_id=key_dict['hdr.bridge_meta.program_id']['value']
        )

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"], ["hdr.ipv4.srcAddr", "ipv4"]]
        return [
            ["hdr.bridge_meta.program_id",              self.program_id,          "exact"]
        ]
    
class WritePhaseMechanism(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.initblock.configure_write_phases_t")
    
    # Action implementations
    def set_write_phases(self, program_id=1, write_s3=0, write_s4=0, write_s5=0, write_s6=0, write_s7=0, write_s8=0, write_s9=0, write_s10=0):

        keys = WritePhaseKeys(program_id)
        action = BaseAction("configure_write_phase", write_s3, write_s4, write_s5, write_s6, write_s7, write_s8, write_s9, write_s10)
        self.add_entry(keys, action)
        # self.set_default_entry(action)
    

    def remove_entries_for_pid(self, pid):
        # Obter todas as entradas instaladas na pre_filter
        table_keys = self.get_all_entries(False)

        for _, key in table_keys:
            key_dict = key.to_dict()
            key_pid = key_dict['hdr.bridge_meta.program_id']['value']

            # Se o program_id for o mesmo, remove entrada
            if key_pid == pid:
                keys = WritePhaseKeys.from_key_dict(key_dict)
                self.delete_entry(keys)