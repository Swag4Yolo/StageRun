from lib.tofino.types import *
from lib.tofino.constants import *

class PortKeys(BaseTableKeys):
    """
    Table Name: port
    Full Name: port.port
    Type: PORT_CFG
    Usage: n/a
    Capacity: 256

    Key Fields:
    Name       Type      Size  Required    Read Only    Mask
    ---------  ------  ------  ----------  -----------  ----------
    $DEV_PORT  EXACT       32  True        False        0xffffffff

    Data Fields:
    Name                      Type      Size  Required    Read Only
    ------------------------  ------  ------  ----------  -----------
    $SPEED                    STRING       0  False       False
    $FEC                      STRING       0  False       False
    $N_LANES                  UINT        32  False       False
    $PORT_ENABLE              BOOL         1  False       False
    $AUTO_NEGOTIATION         STRING       0  False       False
    $LOOPBACK_MODE            STRING       0  False       False
    $TX_MTU                   UINT        32  False       False
    $RX_MTU                   UINT        32  False       False
    $TX_PFC_EN_MAP            UINT        32  False       False
    $RX_PFC_EN_MAP            UINT        32  False       False
    $TX_PAUSE_FRAME_EN        BOOL         1  False       False
    $RX_PAUSE_FRAME_EN        BOOL         1  False       False
    $CUT_THROUGH_EN           BOOL         1  False       False
    $PORT_DIR                 STRING       0  False       False
    $MEDIA_TYPE               STRING       0  False       True
    $SDS_TX_ATTN              UINT        32  False       False
    $SDS_TX_PRE               INT         32  False       False
    $SDS_TX_PRE2              INT         32  False       False
    $SDS_TX_POST              INT         32  False       False
    $SDS_TX_POST2             INT         32  False       False
    $IS_VALID                 BOOL         1  False       True
    $IS_INTERNAL              BOOL         1  False       True
    $CONN_ID                  UINT        32  False       True
    $CHNL_ID                  UINT        32  False       True
    $PORT_UP                  BOOL         1  False       True
    $PORT_NAME                STRING       0  False       True
    $RX_PRSR_PRI_THRESH       UINT        32  False       False
    $TIMESTAMP_1588_DELTA_TX  UINT        16  False       False
    $TIMESTAMP_1588_DELTA_RX  UINT        16  False       False
    $TIMESTAMP_1588_VALID     BOOL         1  False       True
    $TIMESTAMP_1588_VALUE     UINT        64  False       True
    $TIMESTAMP_1588_ID        UINT        32  False       True
    $PLL_OVRCLK               FLOAT        0  False       False

    """

    def __init__(self, dev_port):
        super().__init__()
        self.dev_port = dev_port 
           
    def to_key_list(self):

        # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"]]
        return [
            ["$DEV_PORT", self.dev_port, "exact"],
        ]
        

class PortHDLKeys(BaseTableKeys):

    def __init__(self, front_port, lane):
        super().__init__()
        self.front_port = front_port 
        self.lane = lane 
           
    def to_key_list(self):

        return [
            ["$CONN_ID", self.front_port, "exact"],
            ["$CHNL_ID", self.lane, "exact"],
        ]
        
class PortHDL(BaseTable):
    def __init__(self, runtime):
        super().__init__(runtime, "$PORT_HDL_INFO")
           
    def get_dev_port(self, front_port, lane):
        keys = PortHDLKeys(front_port, lane)
        resp = self.get_entry(keys, False)
        return resp["$DEV_PORT"]
        
        

class PortMechanism(BaseTable):
    def __init__(self, runtime):
        super().__init__(runtime, "$PORT")
        self.port_hdl = PortHDL(runtime)

    def add_port(self, front_port=0, lane=0, speed=PORT_SPEED_100G, fec=FEC_RS, loopback=LOOPBACK_NONE):
        
        dev_port = self.port_hdl.get_dev_port(front_port, lane)

        keys = PortKeys(dev_port)
        action = BaseAction("")
        action.action_params = {
            "action_name": "",
            "params": {
                "$SPEED": speed,
                "$FEC": fec,
                "$PORT_ENABLE": True,
                "$LOOPBACK_MODE": loopback,
            }
        }
        self.add_entry(keys, action)

    def remove_port(self):
        pass
    def modify_port(self):
        pass