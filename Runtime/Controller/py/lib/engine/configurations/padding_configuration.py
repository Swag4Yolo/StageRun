from lib.tofino.types import *
from lib.tofino.constants import *

        
class PaddingInitModeKeys(BaseTableKeys):
    """
    Represents the keys for the P1Table.
    Provides a structured way to define key values with IntelliSense support.
    """
    def __init__(self, enabled=DISABLED, mode=DISABLED, is_shared_enabled=DISABLED, is_instr_executing=DISABLED):
        super().__init__()
        self.enabled = enabled
        self.mode = mode
        self.is_shared_enabled = is_shared_enabled
        self.is_instr_executing = is_instr_executing


    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["res_md.pad_md.enabled", self.enabled, "exact"],
            ["res_md.pad_md.mode", self.mode, "exact"],
            ["hdr.bridge_meta.is_shared_meta_enabled", self.is_shared_enabled, "exact"],
            ["hdr.bridge_meta.is_instr_executing", self.is_instr_executing, "exact"],
        ]
        
class CalculatePaddingKeys(BaseTableKeys):

    def __init__(self, enabled=DISABLED, bytes_to_add=[DISABLED, DISABLED], is_instr_executing=DISABLED):
        super().__init__()
        self.enabled = enabled
        self.bytes_to_add = bytes_to_add
        self.bytes_to_add = bytes_to_add
        self.is_instr_executing = is_instr_executing


    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """
        return [
            ["res_md.pad_md.enabled", self.enabled, "exact"],
            ["hdr.shared_meta.pd_md.bytes_to_add", self.bytes_to_add[0], self.bytes_to_add[1] , "range"],
            ["hdr.bridge_meta.is_instr_executing", self.is_instr_executing, "exact"],
        ]
       

class PaddingInitModes(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.pad_mechanism.padding_init_modes_t")

        ####### MODE PAD #######
        enabled=1
        shared_meta_enabled=0
        pad_mode=MODE_PAD
        is_instr_exec=DISABLED

        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_pad_with_shared")
        self.add_entry(keys, action)

        enabled=1
        shared_meta_enabled=1
        pad_mode=MODE_PAD
        is_instr_exec=DISABLED
        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_pad")
        self.add_entry(keys, action)

        ####### MODE PADTO #######
        enabled=1
        shared_meta_enabled=0
        pad_mode=MODE_PADTO
        is_instr_exec=DISABLED
        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_padto_with_shared")
        self.add_entry(keys, action)

        enabled=1
        shared_meta_enabled=1
        pad_mode=MODE_PADTO
        is_instr_exec=DISABLED
        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_padto")
        self.add_entry(keys, action)

        ####### MODE PADTTERN #######

        enabled=1
        shared_meta_enabled=0
        pad_mode=MODE_PADTTERN
        is_instr_exec=DISABLED
        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_pad_pattern_with_shared")
        self.add_entry(keys, action)


        enabled=1
        shared_meta_enabled=1
        pad_mode=MODE_PADTTERN
        is_instr_exec=DISABLED
        keys = PaddingInitModeKeys(enabled, pad_mode, shared_meta_enabled, is_instr_exec)
        action = BaseAction("conf_mode_pad_pattern")
        self.add_entry(keys, action)

        ####### MODE PADVAR #######

        #enabled=1
        #shared_meta_enabled=0
        #pad_mode=MODE_PADTO
        #
        #bfrt.bytecode_interpreter_speculative.pipe.SwitchIngress.pad_mechanism.padding_init_modes_t.add_with_conf_mode_pad_var_with_shared(
        #    enabled=enabled,
        #    is_shared_meta_enabled=shared_meta_enabled,
        #    mode=pad_mode,
        #
        #)

class CalculatePadding(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.pad_mechanism.calculate_padding_t")
        
        ####### Calculate MAX_PADDING #######

        low=0x8000
        high=0xFFFF
        enabled=1
        is_instr_exec=DISABLED
        keys = CalculatePaddingKeys(enabled, [low, high], is_instr_exec)
        action = BaseAction("negative_bytes_to_add")
        self.add_entry(keys, action)


        low=0x0080
        high=0x7FFF
        enabled=1
        is_instr_exec=DISABLED
        keys = CalculatePaddingKeys(enabled, [low, high], is_instr_exec)
        action = BaseAction("greater_max_padding")
        self.add_entry(keys, action)


        low=0x0080
        high=0x7FFF
        enabled=1
        is_instr_exec=1
        keys = CalculatePaddingKeys(enabled, [low, high], is_instr_exec)
        action = BaseAction("greater_max_padding_recirculated")
        self.add_entry(keys, action)

        low=0x0000
        high=0x007F
        enabled=1
        is_instr_exec=DISABLED
        keys = CalculatePaddingKeys(enabled, [low, high], is_instr_exec)
        action = BaseAction("less_max_padding")
        self.add_entry(keys, action)

        low=0x0000
        high=0x007F
        enabled=1
        is_instr_exec=1
        keys = CalculatePaddingKeys(enabled, [low, high], is_instr_exec)
        action = BaseAction("less_max_padding_recirculated")
        self.add_entry(keys, action)
