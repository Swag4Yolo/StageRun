from lib.tofino.types import *
from lib.tofino.constants import *
# from lib.engine.instructions.instruction_keys import *

class Register(BaseTable):
    def __init__(self, runtime, location):
        self.runtime = runtime
        self.table_name = f"{location}.reg_1_mem"
        self.reg_table = self.runtime.bfrt_info.table_get(self.table_name)

    def clear(self):
        self.reg_table.entry_del(self.runtime.target)
