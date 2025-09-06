from lib.tofino.types import *
from lib.tofino.constants import *

        
class ToFwdKeys(BaseTableKeys):
    def __init__(self, f1_mark_to_drop=DISABLED, f1_fwd_enabled=DISABLED, f2_mark_to_drop=DISABLED, f2_fwd_enabled=DISABLED):
        super().__init__()
        self.f1_mark_to_drop = f1_mark_to_drop
        self.f1_fwd_enabled = f1_fwd_enabled
        self.f2_mark_to_drop = f2_mark_to_drop
        self.f2_fwd_enabled = f2_fwd_enabled


    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            
            ["res_md_f1.mark_to_drop", self.f1_mark_to_drop, "exact"],
            ["res_md_f2.mark_to_drop", self.f2_mark_to_drop, "exact"],
            ["res_md_f1.fwd_md.enabled", self.f1_fwd_enabled, "exact"],
            ["res_md_f2.fwd_md.enabled", self.f2_fwd_enabled, "exact"],
        ]

class ToFwd(BaseTable):
    def __init__(self, runtime, location, stage):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.to_fwd_t")

        fwd_and_enqueue=0

        ### DROP ###
        keys = ToFwdKeys(f1_mark_to_drop=1, f2_mark_to_drop=1, f1_fwd_enabled=0, f2_fwd_enabled=0)
        action = BaseAction("drop")
        self.add_entry(keys, action)
        keys = ToFwdKeys(f1_mark_to_drop=1, f2_mark_to_drop=0, f1_fwd_enabled=0, f2_fwd_enabled=0)
        action = BaseAction("drop")
        self.add_entry(keys, action)
        keys = ToFwdKeys(f1_mark_to_drop=0, f2_mark_to_drop=1, f1_fwd_enabled=0, f2_fwd_enabled=0)
        action = BaseAction("drop")
        self.add_entry(keys, action)

        ### F1 FWD ###
        keys = ToFwdKeys(f1_mark_to_drop=0, f2_mark_to_drop=0, f1_fwd_enabled=1, f2_fwd_enabled=0)
        action = BaseAction("f1_fwd", fwd_and_enqueue)
        self.add_entry(keys, action)
        keys = ToFwdKeys(f1_mark_to_drop=0, f2_mark_to_drop=0, f1_fwd_enabled=1, f2_fwd_enabled=1)
        action = BaseAction("f1_fwd", fwd_and_enqueue)
        self.add_entry(keys, action)
        keys = ToFwdKeys(f1_mark_to_drop=0, f2_mark_to_drop=0, f1_fwd_enabled=0, f2_fwd_enabled=1)
        action = BaseAction("f2_fwd", fwd_and_enqueue)
        self.add_entry(keys, action)


class ExternalVarKeys(BaseTableKeys):
    def __init__(self, f1_update=DISABLED, f2_update = DISABLED):
        super().__init__()
        self.f1_update = f1_update
        self.f2_update = f2_update

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            
            ["res_md_f1.external_var_md.update", self.f1_update, "exact"],
            ["res_md_f2.external_var_md.update", self.f2_update, "exact"],
        ]

class ExternalVar(BaseTable):
    def __init__(self, runtime, location, stage):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.update_external_var_v1_t")

        ### DROP ###
        keys = ExternalVarKeys(f1_update=1, f2_update=0)
        action = BaseAction("update_v1_f1")
        self.add_entry(keys, action)

        keys = ExternalVarKeys(f1_update=0, f2_update=1)
        action = BaseAction("update_v1_f2")
        self.add_entry(keys, action)


class Var1Var3Keys(BaseTableKeys):
    def __init__(self, f1_id=[DISABLED, DISABLED], f2_id=[DISABLED, DISABLED], f1_update=[DISABLED, DISABLED], f2_update = [DISABLED, DISABLED]):
        super().__init__()
        self.f1_id = f1_id
        self.f2_id = f2_id
        self.f1_update = f1_update
        self.f2_update = f2_update

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [

            ["res_md_f1.local_var_md.id", self.f1_id[0], self.f1_id[1], "ternary"],
            ["res_md_f1.local_var_md.update", self.f1_update[0], self.f1_update[1], "ternary"],
            ["res_md_f2.local_var_md.id", self.f2_id[0], self.f2_id[1], "ternary"],
            ["res_md_f2.local_var_md.update", self.f2_update[0], self.f2_update[1], "ternary"],
        ]

class Var1Var3(BaseTable):
    def __init__(self, runtime, location, stage):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.local_var_v1_v3_write_t")

        keys = Var1Var3Keys(f1_id=[1, MASK_LOCAL_VAR], f1_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var1_f1")
        self.add_entry(keys, action)

        keys = Var1Var3Keys(f2_id=[1, MASK_LOCAL_VAR], f2_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var1_f2")
        self.add_entry(keys, action)

        keys = Var1Var3Keys(f1_id=[3, MASK_LOCAL_VAR], f1_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var3_f1")
        self.add_entry(keys, action)

        keys = Var1Var3Keys(f2_id=[3, MASK_LOCAL_VAR], f2_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var3_f2")
        self.add_entry(keys, action)



class Var2Var4Keys(BaseTableKeys):
    def __init__(self, f1_id=[DISABLED, DISABLED], f2_id=[DISABLED, DISABLED], f1_update=[DISABLED, DISABLED], f2_update = [DISABLED, DISABLED]):
        super().__init__()
        self.f1_id = f1_id
        self.f2_id = f2_id
        self.f1_update = f1_update
        self.f2_update = f2_update

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [

            ["res_md_f1.local_var_md.id", self.f1_id[0], self.f1_id[1], "ternary"],
            ["res_md_f1.local_var_md.update", self.f1_update[0], self.f1_update[1], "ternary"],
            ["res_md_f2.local_var_md.id", self.f2_id[0], self.f2_id[1], "ternary"],
            ["res_md_f2.local_var_md.update", self.f2_update[0], self.f2_update[1], "ternary"],
        ]

class Var2Var4(BaseTable):
    def __init__(self, runtime, location, stage):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.local_var_v2_v4_write_t")

        keys = Var2Var4Keys(f1_id=[2, MASK_LOCAL_VAR], f1_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var2_f1")
        self.add_entry(keys, action)

        keys = Var2Var4Keys(f2_id=[2, MASK_LOCAL_VAR], f2_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var2_f2")
        self.add_entry(keys, action)

        keys = Var2Var4Keys(f1_id=[4, MASK_LOCAL_VAR], f1_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var4_f1")
        self.add_entry(keys, action)

        keys = Var2Var4Keys(f2_id=[4, MASK_LOCAL_VAR], f2_update=[1, MASK_FLAG])
        action = BaseAction("update_local_var4_f2")
        self.add_entry(keys, action)


class HeaderWriteKeys(BaseTableKeys):
    def __init__(self, f1_id=DISABLED, f1_update=DISABLED):
        super().__init__()
        self.f1_id = f1_id
        self.f1_update = f1_update

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["res_md_f1.header_md.id", self.f1_id, "exact"],
            ["res_md_f1.header_md.update", self.f1_update, "exact"],
        ]

class HeaderWrite(BaseTable):
    def __init__(self, runtime, location, stage, final_stage = False):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.header_write_t")

        header_id = HEADER_IPV4_TTL
        keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
        action = BaseAction("update_header_ipv4_ttl_f1")
        self.add_entry(keys, action)

        header_id = HEADER_IPV4_DST
        keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
        action = BaseAction("update_header_ipv4_dst_f1")
        self.add_entry(keys, action)
        
        header_id = HEADER_TCP_SEQ_NO
        keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
        action = BaseAction("update_header_tcp_seq_no_f1")
        self.add_entry(keys, action)
        
        header_id = HEADER_TCP_ACK_NO
        keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
        action = BaseAction("update_header_tcp_ack_no_f1")
        self.add_entry(keys, action)

        header_id = HEADER_IPV4_SRC
        keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
        action = BaseAction("update_header_ipv4_src_f1")
        self.add_entry(keys, action)

        if (final_stage):
            header_id = HEADER_TCP_FLAGS
            keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
            action = BaseAction("update_header_tcp_flags_f1")
            self.add_entry(keys, action)

            header_id = HEADER_IPV4_IDENTIFICATION
            keys = HeaderWriteKeys(f1_id=header_id, f1_update=1)
            action = BaseAction("update_header_ipv4_identification")
            self.add_entry(keys, action)



class ActivateKeys(BaseTableKeys):
    def __init__(self, f1_pkt_type=DISABLED, f2_pkt_type=DISABLED):
        super().__init__()
        self.f1_pkt_type = f1_pkt_type
        self.f2_pkt_type = f2_pkt_type

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["res_md_f1.activate_md.pkt_type", self.f1_pkt_type, "exact"],
            ["res_md_f2.activate_md.pkt_type", self.f2_pkt_type, "exact"],
        ]

class Activate(BaseTable):
    def __init__(self, runtime, location, stage):
        super().__init__(runtime, f"{location}.write_phase_s{stage}.need_mirror_t")

        pkt_type = PKT_TYPE_MIRROR
        keys = ActivateKeys(f1_pkt_type=pkt_type)
        action = BaseAction("mirror_f1")
        self.add_entry(keys, action)

        # pkt_type = PKT_TYPE_MIRROR
        # keys = ActivateKeys(f2_pkt_type=pkt_type)
        # action = BaseAction("mirror_f2")
        # self.add_entry(keys, action)
        
