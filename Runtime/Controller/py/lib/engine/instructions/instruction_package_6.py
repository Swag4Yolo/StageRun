from lib.tofino.types import *
from lib.tofino.constants import *
from lib.engine.instructions.instruction_keys import *

class InstructPack6_P2Table(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime, location):
        self.runtime = runtime
        self.table_name = f"{location}.multi_instruction_p2_t"
    
    def initialize_pad_ni(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED], 
                          instr_id=INSTRUCTION_FINISH, mode=DISABLED, value=DISABLED, num_bytes=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("initialize_pad_ni", instr_id, mode, value, num_bytes)
        self.add_entry(keys, action)

    # def initialize_activate_ni(self, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],instr_id=INSTRUCTION_FINISH, program_id=DISABLED, mirror_sid = DISABLED):
    #     keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
    #     action = BaseAction("initialize_activate_ni", instr_id, program_id, mirror_sid)
    #     self.add_entry(keys, action)

    def arith_between_vars_v1_v2(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                   instr_id=INSTRUCTION_FINISH, header_id=DISABLED, header_update=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("arith_between_vars_v1_v2", instr_id, header_id, header_update, var_id, var_update)
        self.add_entry(keys, action)

    def sum_increment_ni(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                   instr_id=INSTRUCTION_FINISH, header_id=DISABLED, header_update=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("sum_increment_ni", instr_id, header_id, header_update, var_id, var_update)
        self.add_entry(keys, action)


    def reg1_old_value_ni(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                          instr_id=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("reg1_old_value_ni", instr_id, var_id, var_update)
        self.add_entry(keys, action)

    def reg1_new_value_ni(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                                    instr_id=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("reg1_new_value_ni", instr_id, var_id, var_update)
        self.add_entry(keys, action)

    def fwd_ni(self, program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
               instr_id=DISABLED, port=DISABLED, qid=DISABLED, mark_to_drop=DISABLED, rts=DISABLED, enabled=ENABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("fwd_ni", instr_id, port, qid, mark_to_drop, rts, enabled)
        self.add_entry(keys, action)
