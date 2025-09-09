# -*- coding:UTF-8 -*-
import traceback
import sys

try:
    import bfrt_grpc.client as gc
except:
    python_v = '{}.{}'.format(sys.version_info.major, sys.version_info.minor)
    sde_install = os.environ['SDE_INSTALL']
    tofino_libs = '{}/lib/python{}/site-packages/tofino'.format(sde_install, python_v)
    sys.path.append(tofino_libs)
    import bfrt_grpc.client as gc

class bfrt_runtime():
    '''
    Class for runtime control plane
    member variables:
     - interface grpc interface
     - target switch target
     - bfrt_info data plane infomation
     - table instance in data plane
     - register instance in data plane
    '''

    def __init__(self, client_id, p4_name):
        self.table = None
        self.register = None
        try:
            self.grpc_setup(client_id, p4_name)
        except Exception as e:
                print(traceback.format_exc())
                exit(1)
        print("connect successfully!")
        print("p4 program: " + p4_name)
        print("client id: " + str(client_id))
        print("\n")
    

    def grpc_setup(self, client_id=0, p4_name=None):
        '''
        Set up connection to gRPC server and bind
        Args: 
            - client_id Client ID
            - p4_name Name of P4 program
        '''
        self.bfrt_info = None

        grpc_addr = 'localhost:50052'        

        self.interface = gc.ClientInterface(grpc_addr, client_id=client_id,
                device_id=0, notifications=None, perform_subscribe=True)
        self.interface.bind_pipeline_config(p4_name)
        self.bfrt_info = self.interface.bfrt_info_get()

        self.target = gc.Target(device_id=0, pipe_id=0xffff)

    def __entry_add__(self, table_name, key_list, data_list, annotation=None):
        '''
        add a table entry
        Args: 
            - table_name entire table name, e.g. SwitchIngress.control_block_name.table_name
            
            - key_list a list of indefinite length includes table key_name, key_value, and match_type , e.g. [["hdr.ipv4.src", "0.0.0.1", "exact"], ["hdr.ipv4.src", "0.0.0.1", "0.0.0.0", "ternary"], ["hdr.ipv4.src", 0, 255, "range"], ["hdr.ipv4.src", "10.0.0.0", 24, "lpm"], ...]
            
            - data_list a one-item list includes a list of [table action data_name and data_value](maybe empty) and action_name, e.g. [[[data_name, data_value], ...], action_name] or [[], action_name]
            
            - annotation list of annotations, e.g. [["hdr.ipv4.src_addr", "ipv4"], ...]
        '''
        self.table = self.bfrt_info.table_get(table_name)

        if annotation:
            for ann in annotation:
                self.table.info.key_field_annotation_add(ann[0], ann[1])
        match = []

        for key in key_list:
            if key[-1] == "exact":
                match.append(gc.KeyTuple(key[0], key[1]))
            if key[-1] == "ternary":
                match.append(gc.KeyTuple(key[0], key[1], key[2]))
            if key[-1] == "range":
                match.append(gc.KeyTuple(key[0], low=key[1], high=key[2]))
            if key[-1] == "lpm":
                match.append(gc.KeyTuple(key[0], key[1], prefix_len=key[2]))
        
        action = []

        if len(data_list[0]) != 0:
            for data in data_list[0]:
                field_name = data[0]
                value = data[1]
                if isinstance(value, bool):
                    action.append(gc.DataTuple(field_name, bool_val=value))
                elif isinstance(value, str):
                    action.append(gc.DataTuple(field_name, str_val=value))
                else:
                    action.append(gc.DataTuple(field_name, value))
        ### if action_name
        if data_list[1] == "":
            self.table.entry_add(self.target, [self.table.make_key(match)], [self.table.make_data(action)])
        else:
            self.table.entry_add(self.target, [self.table.make_key(match)], [self.table.make_data(action, data_list[1])])

    def __entry_del__(self, table_name, key_list, annotation=None):
        '''
        delete a table entry
        Args:
            - table_name entire table name, e.g. SwitchIngress.control_block_name.table_name
            - key_list a list of indefinite length includes table key_name, key_value, and match_type , e.g. [["hdr.ipv4.src", "0.0.0.1", "exact"], ["hdr.ipv4.src", "0.0.0.1", "0.0.0.0", "ternary"], ["hdr.ipv4.src", 0, 255, "range"], ["hdr.ipv4.src", "10.0.0.0", 24, "lpm"], ...]
            - annotation list of annotations, e.g. [["hdr.ipv4.src_addr", "ipv4"], ...]
        '''
        self.table = self.bfrt_info.table_get(table_name)
        if annotation:
            for ann in annotation:
                self.table.info.key_field_annotation_add(ann[0], ann[1])

        match = []
        for key in key_list:
            if key[-1] == "exact":
                match.append(gc.KeyTuple(key[0], key[1]))
            if key[-1] == "ternary":
                match.append(gc.KeyTuple(key[0], key[1], key[2]))
            if key[-1] == "range":
                match.append(gc.KeyTuple(key[0], low=key[1], high=key[2]))
            if key[-1] == "lpm":
                match.append(gc.KeyTuple(key[0], key[1], prefix_len=key[2]))
    
        self.table.entry_del(self.target, [self.table.make_key(match)])

    def __entry_set_default__(self, table_name, data_list, annotation=None):
        self.table = self.bfrt_info.table_get(table_name)
        if annotation:
            for ann in annotation:
                self.table.info.key_field_annotation_add(ann[0], ann[1])

        action = []

        if len(data_list[0]) != 0:
            for data in data_list[0]:
                action.append(gc.DataTuple(data[0], data[1]))
        
        [self.table.make_data(action, data_list[1])]
        action_data = self.table.make_data(
            action_name=data_list[1],
            data_field_list_in=action
        )

        self.table.default_entry_set(target=self.target, data=action_data)

    def __entry_reset__(self, table_name):
        self.table = self.bfrt_info.table_get(table_name)
        self.table.default_entry_reset(self.target)

    def __table_clear__(self, table_name):
        self.table = self.bfrt_info.table_get(table_name)

        # get all keys in table
        resp = self.table.entry_get(self.target, [], {"from_hw": False})

        # delete all keys in table
        for _, key in resp:
            if key:
                self.table.entry_del(self.target, [key])


    def __entry_get__(self, table_name, key_list, from_hw):
        self.table = self.bfrt_info.table_get(table_name)

        match = []
        for key in key_list:
            if key[-1] == "exact":
                match.append(gc.KeyTuple(key[0], key[1]))
            if key[-1] == "ternary":
                match.append(gc.KeyTuple(key[0], key[1], key[2]))
            if key[-1] == "range":
                match.append(gc.KeyTuple(key[0], low=key[1], high=key[2]))
            if key[-1] == "lpm":
                match.append(gc.KeyTuple(key[0], key[1], prefix_len=key[2]))
        
        resp = self.table.entry_get(self.target, [self.table.make_key(match)], {"from_hw": from_hw})
        data_dict = next(resp)[0].to_dict()
        return data_dict
    
    def __entry_get_all__(self, table_name, from_hw):
        self.table = self.bfrt_info.table_get(table_name)
        
        resp = self.table.entry_get(self.target, [], {"from_hw": from_hw})
        return resp
        # data_dict = next(resp)[0].to_dict()
        # return data_dict

    def get_dev_port(self, front_panel_port, lane):        
        
        port_hdl_info_table = self.bfrt_info.table_get("$PORT_HDL_INFO")
        
        # convert front-panel port to dev port
        resp = port_hdl_info_table.entry_get(
            self.target,
            [port_hdl_info_table.make_key([gc.KeyTuple('$CONN_ID', front_panel_port),
                                           gc.KeyTuple('$CHNL_ID', lane)])], {"from_hw": False})

        dev_port = next(resp)[0].to_dict()["$DEV_PORT"]

        return dev_port


    # def reg_read(self, reg_name, index):
    #     '''
    #     read one block's value of a register
    #     Args: 
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - index register index
    #     retuen a int value
    #     '''

    #     self.register = self.bfrt_info.table_get(reg_name)
    #     snap = self.register.entry_get(self.target, [self.register.make_key([gc.KeyTuple('$REGISTER_INDEX', index)])],{"from_hw": True})
    #     data, _ = next(snap)
    #     data_dict = data.to_dict()
    #     value = data_dict[reg_name + ".f1"][0]
    #     return value

    # def reg_read_range(self, reg_name, low=0, high=0):
    #     '''
    #     read a range of values of a register
    #     Args:
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - low the lower bound of the index you want to get
    #         - high the upper bound of the  index you want to get
    #     return a list of value from reg[low] to reg[high-1]
    #     '''

    #     self.register = self.bfrt_info.table_get(reg_name)
    #     value_list = []
    #     key_list = []
    #     for i in range(low, high):
    #         key_list.append(self.register.make_key([gc.KeyTuple('$REGISTER_INDEX', i)]))
    #     resp = self.register.make_key(key_list, {"from_hw": True})
    #     for data, _ in resp:
    #         data_dict = data.to_dict()
    #         value = data_dict[reg_name + ".f1"][0]
    #         value_list.append(value)
    #     return value_list
    
    # def reg_modify(self, reg_name, index, value):
    #     '''
    #     modify one block's value of a register
    #     Args:
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - index register index
    #         - value the new value you want to modify
    #     '''
    #     self.register = self.bfrt_info.table_get(reg_name)
    #     key = [self.register.make_key(gc.KeyTuple("$REGISTER_INDEX",index))]
    #     data = [self.register.make_data([gc.DataTuple(reg_name + ".f1", value)])]
    #     self.register.entry_add(self.target, key, data)
    
    # def reg_modify_range(self, reg_name, low=0, high=0, values=[]):
    #     '''
    #     modify a range of value of a register
    #     Args:
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - low the lower bound of the index you want to modify
    #         - high the upper bound of the index you want to modify
    #         - values a list of value you want to modify, the length of the list should be high - low. 
    #     '''
    #     self.register = self.bfrt_info.table_get(reg_name)
    #     key_list = []
    #     data_list = []
    #     for i in range(low, high):
    #         key_list.append(self.register.make_key([gc.KeyTuple('$REGISTER_INDEX', i)]))
    #         data_list.append(self.register.make_data([gc.DataTuple(reg_name + ".f1", values[i - low])]))
    #     self.register.entry_add(self.target, key_list, data_list)

    # def reg_clear(self, reg_name, index):
    #     '''
    #     clear one block's value of a register
    #     Args:
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - index register index
    #     '''
    #     self.register = self.bfrt_info.table_get(reg_name)
    #     key = [self.register.make_key(gc.KeyTuple("$REGISTER_INDEX",index))]
    #     data = [self.register.make_data([gc.DataTuple(reg_name + ".f1", 0)])]
    #     self.register.entry_add(self.target, key, data)
    
    # def reg_clear_range(self, reg_name, low=0, high=0):
    #     '''
    #     clear a range of value of a register
    #     Args:
    #         - reg_name entire register name, e.g. SwitchIngress.control_block_name.reg_name
    #         - low the lower bound of the index you want to clear
    #         - high the upper bound of the index you want to clear
    #     '''
    #     self.register = self.bfrt_info.table_get(reg_name)
    #     key_list = []
    #     data_list = []
    #     for i in range(low, high):
    #         key_list.append(self.register.make_key([gc.KeyTuple('$REGISTER_INDEX', i)]))
    #         data_list.append(self.register.make_data([gc.DataTuple(reg_name + ".f1", 0)]))
    #     self.register.entry_add( self.conn, key_list, data_list)
