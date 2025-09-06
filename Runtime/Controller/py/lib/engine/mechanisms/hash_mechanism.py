from lib.tofino.types import *
from lib.tofino.constants import *

import traceback
import sys
import os
try:
    import bfrt_grpc.client as gc
except:
    python_v = '{}.{}'.format(sys.version_info.major, sys.version_info.minor)
    sde_install = os.environ['SDE_INSTALL']
    tofino_libs = '{}/lib/python{}/site-packages/tofino'.format(sde_install, python_v)
    sys.path.append(tofino_libs)
    import bfrt_grpc.client as gc
        
class HashMechanism(BaseTable):

    KeysSupportedList = {
    # Note: they all have + 8bits that real
            'eth_src_addr'  :   56,
            'ipv4_src_addr' :   40,
            'ipv4_dst_addr' :   40,
            'ipv4_protocol' :   16,
            'l4_src_port'   :   24,
            'l4_dst_port'   :   24,
            'field1'   :   32,

    }
    def __init__(self, runtime, table_name):
        super().__init__(runtime, table_name+'.configure')
    

    # @staticmethod
    def __aux(self, field_name:str, elements:list):
        order       = elements[0]
        start_bit   = elements[1]
        length      = elements[2]

        # field_name = "hdr.ipv4.srcAddr"
        value = [{          "order":     gc.DataTuple("order", order),
                            "start_bit": gc.DataTuple("start_bit", start_bit),
                            "length":    gc.DataTuple("length", length)
                }]
        return gc.DataTuple(field_name, container_arr_val = value)

    # Action implementations
    def set_hash_mechanism(self, keys = [HASH_ETH_SRC_ADDR, HASH_IPV4_SRC_ADDR, HASH_IPV4_DST_ADDR, HASH_IPV4_PROTO, HASH_L4_SPORT, HASH_L4_DPORT, HASH_FIELD1]):

        order = 1
        l = []
        d = dict(self.KeysSupportedList)

        for key in keys:
            length = self.KeysSupportedList[key] - 8
            #start_bit 0 => starts counting from the first bit
            start_bit = 0
            l.append(self.__aux(key, [order, start_bit,  length]))
            del d[key]
            order += 1

        for key in d:
            #Keys that were not selected
            #So need to be disabled
            length = 1
            start_bit = d[key] - 1
            l.append(self.__aux(key, [order, start_bit,  length]))
            order += 1


        # Hash Mechanism are a special default_entry_set since they are not the default action of a table, and so they do not have a default_action_name
        table = self.runtime.bfrt_info.table_get(self.table_name)
        data = table.make_data(l)
        table.default_entry_set(target=self.runtime.target, data=data)
    
