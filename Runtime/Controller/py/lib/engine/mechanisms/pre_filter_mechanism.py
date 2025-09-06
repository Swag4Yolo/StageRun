from lib.tofino.types import *
from lib.tofino.constants import *

class PreFilterKeys(BaseTableKeys):
    def __init__(self, ig_port=[0,0], original_ig_port=[0,0], total_pkt_len=[0,0], tcp_dst_port=[0,0], ipv4_dst_addr=[0,0], tcp_flags= [0,0], ipv4_proto=[0,0], ipv4_src_addr=[0,0], udp_sport=[0,0], udp_dport=[0,0], program_id=0):
        super().__init__()
        self.ig_port            = ig_port
        self.original_ig_port   = original_ig_port
        self.total_pkt_len      = total_pkt_len
        self.tcp_dst_port       = tcp_dst_port
        self.ipv4_src_addr      = ipv4_src_addr
        self.ipv4_dst_addr      = ipv4_dst_addr
        self.tcp_flags          = tcp_flags
        self.ipv4_proto         = ipv4_proto
        self.udp_sport          = udp_sport
        self.udp_dport          = udp_dport
        self.program_id         = program_id

    def to_key_list(self):
        """
        Converts the key values to the format required by the runtime.
        """

        self.annotations = [["hdr.ipv4.dstAddr", "ipv4"], ["hdr.ipv4.srcAddr", "ipv4"]]
        return [
            ["ig_intr_md.ingress_port",                 self.ig_port[0],           self.ig_port[1],             "ternary"],
            ["hdr.bridge_meta.original_ingress_port",   self.original_ig_port[0],  self.original_ig_port[1],    "ternary"],
            ["hdr.ipv4.totalLen",                       self.total_pkt_len[0],     self.total_pkt_len[1],       "ternary"],
            ["hdr.tcp.dst_port",                        self.tcp_dst_port[0],      self.tcp_dst_port[1],        "ternary"],
            ["hdr.ipv4.srcAddr",                        self.ipv4_src_addr[0],     self.ipv4_src_addr[1],       "ternary"],
            ["hdr.ipv4.dstAddr",                        self.ipv4_dst_addr[0],     self.ipv4_dst_addr[1],       "ternary"],
            ["hdr.tcp.flags",                           self.tcp_flags[0],         self.tcp_flags[1],           "ternary"],
            ["hdr.ipv4.protocol",                       self.ipv4_proto[0],        self.ipv4_proto[1],          "ternary"],
            ["hdr.udp.src_port",                        self.udp_sport[0],         self.udp_sport[1],           "ternary"],
            ["hdr.udp.dst_port",                        self.udp_dport[0],         self.udp_dport[1],           "ternary"],
            ["hdr.bridge_meta.program_id",              self.program_id,          "exact"]
        ]
        
class PreFilterMechanism(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.pre_filter_mechanism.pkt_filter_t")
    
    # Action implementations
    def set_pkt_id(self, ig_port=[0,0], original_ig_port=[0,0], total_pkt_len=[0,0], tcp_dst_port=[0,0], ipv4_src_addr=[0,0], ipv4_dst_addr=[0,0], tcp_flags=[0,0], pkt_id=0, ni_f1=INSTRUCTION_FINISH, ni_f2=INSTRUCTION_FINISH, ipv4_proto=[0,0], udp_sport=[0,0], udp_dport=[0,0], program_id=1):
        keys = PreFilterKeys(ig_port, original_ig_port, total_pkt_len, tcp_dst_port, ipv4_dst_addr, tcp_flags, ipv4_proto, ipv4_src_addr, udp_sport, udp_dport, program_id)
        action = BaseAction("set_pkt_id", pkt_id, ni_f1, ni_f2)
        self.add_entry(keys, action)
    
    # Action implementations
    def set_pkt_id_only(self, ig_port=[0,0], original_ig_port=[0,0], total_pkt_len=[0,0], tcp_dst_port=[0,0], ipv4_src_addr=[0,0], ipv4_dst_addr=[0,0], tcp_flags=[0,0], pkt_id=0, ipv4_proto=[0,0], udp_sport=[0,0], udp_dport=[0,0], program_id=1):
        keys = PreFilterKeys(ig_port, original_ig_port, total_pkt_len, tcp_dst_port, ipv4_dst_addr, tcp_flags, ipv4_proto, ipv4_src_addr, udp_sport, udp_dport, program_id)
        action = BaseAction("set_pkt_id_only", pkt_id)
        self.add_entry(keys, action)
    

class GenericFwdKeys(BaseTableKeys):
    def __init__(self, pkt_id=PKT_FILTER_DEFAULT, program_id=1):
        super().__init__()
        self.pkt_id            = pkt_id
        self.program_id        = program_id

    def to_key_list(self):
        return [
            ["hdr.bridge_meta.program_id", self.program_id, "exact"],
            ["ig_md.pkt_filter_md.pkt_id", self.pkt_id, "exact"],
        ]

class GenericFwd(BaseTable):

    def __init__(self, runtime, location):
        super().__init__(runtime, f"{location}.pre_filter_mechanism.generic_fwd_t")

    def drop(self, pkt_id, port, program_id):
        keys = GenericFwdKeys(pkt_id, program_id)
        action = BaseAction("drop", pkt_id, port)
        self.add_entry(keys, action)
    
    def fwd(self, pkt_id, port, program_id):
        keys = GenericFwdKeys(pkt_id, program_id)
        action = BaseAction("fwd", port)
        self.add_entry(keys, action)

    def fwd_and_enqueue(self, pkt_id, program_id, port, qid):
        keys = GenericFwdKeys(pkt_id, program_id)
        action = BaseAction("fwd_and_enqueue", port, qid)
        self.add_entry(keys, action)