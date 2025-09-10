from lib.tofino.types import *
from lib.tofino.constants import *
from lib.engine.instructions.instruction_keys import *

class InstructPackInit_P2Table(BaseTable):
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

    def initialize_activate_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],instr_id=INSTRUCTION_FINISH, mirror_sid = DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("initialize_activate_ni", instr_id, program_id, mirror_sid)
        self.add_entry(keys, action)


    def sum_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                   instr_id=INSTRUCTION_FINISH, const_val=DISABLED, header_id=DISABLED, header_update=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("sum_ni", instr_id, const_val, header_id, header_update, var_id, var_update)
        self.add_entry(keys, action)


    def complement_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                   instr_id=INSTRUCTION_FINISH, header_id=DISABLED, header_update=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("complement_ni", instr_id, header_id, header_update, var_id, var_update)
        self.add_entry(keys, action)

    def mul_4x_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                   instr_id=INSTRUCTION_FINISH, header_id=DISABLED, header_update=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("mul_4x_ni", instr_id, header_id, header_update, var_id, var_update)
        self.add_entry(keys, action)


    def reg1_old_value_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                          instr_id=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("reg1_old_value_ni", instr_id, var_id, var_update)
        self.add_entry(keys, action)

    def reg1_new_value_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                                    instr_id=DISABLED, var_id=DISABLED, var_update=DISABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("reg1_new_value_ni", instr_id, var_id, var_update)
        self.add_entry(keys, action)

    def fwd_ni(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
               instr_id=DISABLED, port=DISABLED, qid=DISABLED, mark_to_drop=DISABLED, rts=DISABLED, enabled=ENABLED):
        keys = P2TableKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("fwd_ni", instr_id, port, qid, mark_to_drop, rts, enabled)
        self.add_entry(keys, action)

class InstructPackInitSpeculative(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime, location):
        self.runtime = runtime
        self.table_name = f"{location}.speculative_t"
    
    def speculative_conditional_v1_v2(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                            instr_id=DISABLED, cond_mode=DISABLED, cond_val=DISABLED, cond_mode_2=DISABLED, cond_val_2=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_conditional_v1_v2", instr_id, cond_mode, cond_val, cond_mode_2, cond_val_2)
        self.add_entry(keys, action)

    def speculative_conditional_v3_v4(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                            instr_id=DISABLED, cond_mode=DISABLED, cond_val=DISABLED, cond_mode_2=DISABLED, cond_val_2=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_conditional_v3_v4", instr_id, cond_mode, cond_val, cond_mode_2, cond_val_2)
        self.add_entry(keys, action)

    def speculative_set_index_ingress_port_w_const_val(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                        instr_id=DISABLED, mode=DISABLED, mem_const_val=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_ingress_port_w_const_val", instr_id, mode, mem_const_val)
        self.add_entry(keys, action)

    def speculative_set_index_ingress_port_w_global_var_pkt_size(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED], instr_id=DISABLED, mode=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_ingress_port_w_global_var_pkt_size",instr_id, mode)
        self.add_entry(keys, action)

    def speculative_set_index_hash_1_w_const_val(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                    instr_id=DISABLED, mode=DISABLED, mem_const_val=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_hash_1_w_const_val", instr_id, mode, mem_const_val)
        self.add_entry(keys, action)

    def speculative_set_index_hash_1_w_global_var_pkt_size(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED], instr_id=DISABLED, mode=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_hash_1_w_global_var_pkt_size", instr_id, mode)
        self.add_entry(keys, action)

    def speculative_set_index_hash_1_w_var(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED], instr_id=DISABLED, mode=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_hash_1_w_var", instr_id, mode)
        self.add_entry(keys, action)

    def speculative_set_index_hash_2_w_const_val(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                                    instr_id=DISABLED, mode=DISABLED, mem_const_val=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_hash_2_w_const_val", instr_id, mode, mem_const_val)
        self.add_entry(keys, action)

    def speculative_set_index_hash_2_w_global_var_pkt_size(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                        instr_id=DISABLED, mode=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_set_index_hash_2_w_global_var_pkt_size", instr_id, mode)
        self.add_entry(keys, action)

    def speculative_fetch_v1(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_v1", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_v2(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_v2", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_hash_1(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_hash_1", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_tcp_ack(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_tcp_ack", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_tcp_seq(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_tcp_seq", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_ipv4_total_len(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_ipv4_total_len", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_fetch_tcp_data_offset(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_tcp_data_offset", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)
        
    def speculative_fetch_ipv4_ihl(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED, var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_ipv4_ihl", instr_id, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)


    def speculative_fetch_const_val(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                instr_id=DISABLED,
                                const_val=DISABLED,var_to_header=DISABLED, header_to_var=DISABLED, external_var_update=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_fetch_const_val", instr_id, const_val, var_to_header, header_to_var, external_var_update)
        self.add_entry(keys, action)

    def speculative_conditional_between_vars(self,  program_id=1, ni=INSTRUCTION_FINISH, pkt_id=[DISABLED, DISABLED], cm=[DISABLED, DISABLED], cval=[DISABLED, DISABLED], cm_2 = [DISABLED, DISABLED], cval_2 = [DISABLED, DISABLED],
                                                instr_id=DISABLED, cond_mode=DISABLED, cond_mode_2=DISABLED):
        keys = SpeculativeKeys(program_id, ni, pkt_id, cm, cval, cm_2, cval_2)
        action = BaseAction("speculative_conditional_between_vars", instr_id, cond_mode, cond_mode_2)
        self.add_entry(keys, action)
