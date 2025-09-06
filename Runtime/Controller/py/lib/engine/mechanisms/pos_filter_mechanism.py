from lib.tofino.types import *
from lib.tofino.constants import *

class PosFilterKeys(BaseTableKeys):
    """
    Represents the keys for the MultiInstructionP1Table.
    Provides a structured way to define key values with IntelliSense support.
    """
    def __init__(self, f1_mark_to_drop=[DISABLED, DISABLED], f2_mark_to_drop=[DISABLED, DISABLED], need_recirc=[DISABLED, DISABLED], fwd_and_enqueue=[DISABLED, DISABLED], rts=[DISABLED, DISABLED], f1_next_instr=[DISABLED, DISABLED], f2_next_instr=[DISABLED, DISABLED], ingress_port=[DISABLED, DISABLED], original_ingress_port=[DISABLED, DISABLED], ipv4_total_len=[DISABLED, DISABLED], tcp_dport=[DISABLED, DISABLED], ipv4_dst=[DISABLED, DISABLED], ipv4_proto=[DISABLED, DISABLED]):
        super().__init__()
        self.f1_mark_to_drop = f1_mark_to_drop
        self.f2_mark_to_drop = f2_mark_to_drop
        self.need_recirc = need_recirc
        self.fwd_and_enqueue = fwd_and_enqueue
        self.rts = rts
        self.f1_next_instr = f1_next_instr
        self.f2_next_instr = f2_next_instr
        self.ingress_port = ingress_port
        self.original_ingress_port = original_ingress_port
        self.ipv4_total_len = ipv4_total_len
        self.tcp_dport = tcp_dport
        self.ipv4_dst = ipv4_dst
        self.ipv4_proto = ipv4_proto

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        self.annotations = [["hdr.ipv4.dstAddr", "ipv4"]]
        return [
            ["res_md_f1.mark_to_drop", self.f1_mark_to_drop[0], self.f1_mark_to_drop[1],            "ternary"],
            ["res_md_f2.mark_to_drop", self.f2_mark_to_drop[0], self.f2_mark_to_drop[1],            "ternary"],
            ["hdr.bridge_meta.need_recirc", self.need_recirc[0], self.need_recirc[1],               "ternary"],
            ["hdr.bridge_meta.fwd_and_enqueue", self.fwd_and_enqueue[0], self.fwd_and_enqueue[1] ,  "ternary"],
            ["hdr.bridge_meta.rts", self.rts[0], self.rts[1] ,                                      "ternary"],
            ["hdr.bridge_meta.f1.next_instruction", self.f1_next_instr[0], self.f1_next_instr[1] ,  "ternary"],
            ["hdr.bridge_meta.f2.next_instruction", self.f2_next_instr[0], self.f2_next_instr[1] ,  "ternary"],
            ["ig_intr_md.ingress_port", self.ingress_port[0], self.ingress_port[1] ,                "ternary"],
            ["hdr.bridge_meta.original_ingress_port", self.original_ingress_port[0], self.original_ingress_port[1] ,"ternary"],
            ["hdr.ipv4.totalLen", self.ipv4_total_len[0], self.ipv4_total_len[1] ,                 "ternary"],
            ["hdr.tcp.dst_port", self.tcp_dport[0], self.tcp_dport[1] ,                             "ternary"],
            ["hdr.ipv4.dstAddr", self.ipv4_dst[0], self.ipv4_dst[1] ,                               "ternary"],
            ["ig_md.keys.ipv4_protocol", self.ipv4_proto[0], self.ipv4_proto[1] ,                   "ternary"],
        ]
        
class PosFilterMechanism(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.recircblock.recirculation_t")
    
    def _begin_rules(self):
        ### Drop Rules ###

        keys = PosFilterKeys(f1_mark_to_drop=[1, 0x1])
        action = BaseAction("drop")
        self.add_entry(keys, action)

        keys = PosFilterKeys(f2_mark_to_drop=[1, 0x1])
        action = BaseAction("drop")
        self.add_entry(keys, action)

        ### RTS ###
        keys = PosFilterKeys(rts=[1, 0x1])
        action = BaseAction("rts_fwd")
        self.add_entry(keys, action)

        ### Pos Filter Rules ###

    def _last_rules(self):
        ### Default Forwaring ###
        keys = PosFilterKeys(need_recirc=[0, 0x1])
        action = BaseAction("set_egress_port")
        self.add_entry(keys, action)


    # Action implementations
    def pos_filter_fwd(self, original_ig_port=[DISABLED, DISABLED], ipv4_proto=[DISABLED, DISABLED], ipv4_total_len=[DISABLED, DISABLED], port=DISABLED):

        keys = PosFilterKeys(original_ingress_port=original_ig_port, ipv4_proto=ipv4_proto, ipv4_total_len=ipv4_total_len)
        action = BaseAction("pos_filter_fwd", port)
        self.add_entry(keys, action)

    
    # Action implementations
    def pos_filter_fwd_and_enqueue(self, original_ig_port=[DISABLED, DISABLED], ipv4_proto=[DISABLED, DISABLED], ipv4_total_len=[DISABLED, DISABLED], port=DISABLED, qid=DISABLED):

        keys = PosFilterKeys(original_ingress_port=original_ig_port, ipv4_proto=ipv4_proto, ipv4_total_len=ipv4_total_len)
        action = BaseAction("pos_filter_fwd_and_enqueue", port, qid)
        self.add_entry(keys, action)
    
    # Action implementations
    def pos_filter_recirc_same_pipe(self, f1_next_instr=[DISABLED, DISABLED],f2_next_instr=[DISABLED, DISABLED]):

        keys = PosFilterKeys(f1_next_instr=f1_next_instr, f2_next_instr=f2_next_instr, original_ingress_port=[0x000, 0x180])
        action = BaseAction("recirculate_p0")
        self.add_entry(keys, action)

        keys = PosFilterKeys(f1_next_instr=f1_next_instr, f2_next_instr=f2_next_instr, original_ingress_port=[0x080, 0x180])
        action = BaseAction("recirculate_p1")
        self.add_entry(keys, action)

        keys = PosFilterKeys(f1_next_instr=f1_next_instr, f2_next_instr=f2_next_instr, original_ingress_port=[0x0100, 0x180])
        action = BaseAction("recirculate_p2")
        self.add_entry(keys, action)

        keys = PosFilterKeys(f1_next_instr=f1_next_instr, f2_next_instr=f2_next_instr, original_ingress_port=[0x0180, 0x180])
        action = BaseAction("recirculate_p3")
        self.add_entry(keys, action)

    
    

