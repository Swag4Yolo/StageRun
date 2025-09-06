from lib.tofino.types import *
from lib.tofino.constants import *

class CloneKeys(BaseTableKeys):
    """

    Table Name: cfg
    Full Name: mirror.cfg
    Type: MIRROR_CFG
    Usage: 0
    Capacity: 1024

    Key Fields:
    Name    Type      Size  Required    Read Only    Mask
    ------  ------  ------  ----------  -----------  ------
    $sid    EXACT       16  True        False        0xffff

    Data Fields for action $coalescing:
    Name                      Type           Size  Required    Read Only
    ------------------------  -----------  ------  ----------  -----------
    $internal_header          BYTE_STREAM     128  False       False
    $internal_header_length   UINT             32  False       False
    $timeout_usec             UINT             32  False       False
    $extract_len              UINT             32  False       False
    $session_enable           BOOL              1  False       False
    $direction                STRING            0  False       False
    $ucast_egress_port        UINT             32  False       False
    $ucast_egress_port_valid  BOOL              1  False       False
    $egress_port_queue        UINT             32  False       False
    $ingress_cos              UINT             32  False       False
    $packet_color             STRING            0  False       False
    $level1_mcast_hash        UINT             32  False       False
    $level2_mcast_hash        UINT             32  False       False
    $mcast_grp_a              UINT             16  False       False
    $mcast_grp_a_valid        BOOL              1  False       False
    $mcast_grp_b              UINT             16  False       False
    $mcast_grp_b_valid        BOOL              1  False       False
    $mcast_l1_xid             UINT             16  False       False
    $mcast_l2_xid             UINT             16  False       False
    $mcast_rid                UINT             16  False       False
    $icos_for_copy_to_cpu     UINT             32  False       False
    $copy_to_cpu              BOOL              1  False       False
    $max_pkt_len              UINT             16  False       False

    Data Fields for action $normal:
    Name                      Type      Size  Required    Read Only
    ------------------------  ------  ------  ----------  -----------
    $session_enable           BOOL         1  False       False
    $direction                STRING       0  False       False
    $ucast_egress_port        UINT        32  False       False
    $ucast_egress_port_valid  BOOL         1  False       False
    $egress_port_queue        UINT        32  False       False
    $ingress_cos              UINT        32  False       False
    $packet_color             STRING       0  False       False
    $level1_mcast_hash        UINT        32  False       False
    $level2_mcast_hash        UINT        32  False       False
    $mcast_grp_a              UINT        16  False       False
    $mcast_grp_a_valid        BOOL         1  False       False
    $mcast_grp_b              UINT        16  False       False
    $mcast_grp_b_valid        BOOL         1  False       False
    $mcast_l1_xid             UINT        16  False       False
    $mcast_l2_xid             UINT        16  False       False
    $mcast_rid                UINT        16  False       False
    $icos_for_copy_to_cpu     UINT        32  False       False
    $copy_to_cpu              BOOL         1  False       False
    $max_pkt_len              UINT        16  False       False

    """

    def __init__(self, sid):
        super().__init__()
        self.sid = sid 
           
    def to_key_list(self):

        # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"]]
        return [
            ["$sid", self.sid, "exact"],
        ]
        
class CloneMechanism(BaseTable):
    """
    Represents the multi_instruction_p1_t table, encapsulating its keys, actions, and functionality.
    """

    def __init__(self, runtime):
        super().__init__(runtime, "$mirror.cfg")
        
    
    # Action implementations
    def normal_cloning(self, sid=1, direction=MIRROR_DIR_INGRESS, ucast_egress_port=68, session_enable=True, ucast_egress_port_valid=True, egress_port_queue=0):

        keys = CloneKeys(sid)
        action = BaseAction("")
        action.action_params = {
            "action_name": "$normal",
            "params": {
                "$direction": direction,
                "$ucast_egress_port": ucast_egress_port,
                "$session_enable": session_enable,
                "$ucast_egress_port_valid": ucast_egress_port_valid,
                "$egress_port_queue": egress_port_queue,
            }
        }
        self.add_entry(keys, action)