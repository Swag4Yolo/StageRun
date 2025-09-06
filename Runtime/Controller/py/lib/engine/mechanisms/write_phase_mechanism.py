from lib.tofino.types import *
from lib.tofino.constants import *
     
class WritePhaseMechanism(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.initblock.configure_write_phases_t")
    
    # Action implementations
    def set_write_phases(self, write_s3=0, write_s4=0, write_s5=0, write_s6=0, write_s7=0, write_s8=0, write_s9=0, write_s10=0):

        action = BaseAction("configure_write_phase", write_s3, write_s4, write_s5, write_s6, write_s7, write_s8, write_s9, write_s10)

        self.set_default_entry(action)
    
