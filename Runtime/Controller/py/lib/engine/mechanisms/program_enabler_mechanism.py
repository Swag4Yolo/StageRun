from lib.tofino.types import *
from lib.tofino.constants import *
     
class ProgramEnablerMechanism(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.initblock.is_program_enabled_t")
    
    # Action implementations
    def enable_program(self):
        action = BaseAction("set_program_enabled")
        self.set_default_entry(action)

    def disable_program(self):
        action = BaseAction("set_program_disabled")
        self.set_default_entry(action)

