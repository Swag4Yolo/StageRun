import ipaddress

from lib.controller.deployer.types import *
from lib.controller.constants import *
from lib.tofino.constants import *
from lib.utils.manifest_parser import get_pnum_from_endpoints
import lib.controller.state_manager as sm

from Core.ast_nodes import *
import json


def cidr_to_ip_and_mask(ip_cidr: str):
    """Converts CIDR (e.g. '10.10.1.0/24') to (ip_int, mask_int)."""
    network = ipaddress.IPv4Network(ip_cidr, strict=False)
    ip_int = int(network.network_address)
    mask_int = int(network.netmask)
    return ip_int, mask_int

class MicroInstructionError(Exception):
    pass


class MicroInstructionParser():

    def __init__(self):
        pass

    @staticmethod
    def translate_keys_to_micro(prefilter:PreFilterNode, manifest, pid) -> PreFilterKeys:
        # Defaults para todos os campos aceites pelo set_pkt_id()
        args = {
            # Table Keys
            "ig_port": [0, 0],
            "original_ig_port": [0, 0],
            "total_pkt_len": [0, 0],
            "tcp_dst_port": [0, 0],
            "ipv4_src_addr": [0, 0],
            "ipv4_dst_addr": [0, 0],
            "tcp_flags": [0, 0],
            "ipv4_proto": [0, 0],
            "udp_sport": [0, 0],
            "udp_dport": [0, 0],

            # Action Parameters
            "pkt_id": 0,
            "ni_f1": INSTRUCTION_FINISH,
            "ni_f2": INSTRUCTION_FINISH,
            "program_id": pid
        }

        # Preenche com base nas keys do prefilter
        for key in prefilter.keys:
            field = key.field
            operand = key.operand
            value = key.value

            if operand == "EQ":
                if field == "PKT.PORT":
                    port = get_pnum_from_endpoints(manifest, value)
                    dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(port, 0)
                    args["ig_port"] = [dev_port, MASK_PORT]

                elif field == "IPV4.DST":
                    ip_cidr = value  # e.g. "10.10.1.0/24"
                    ip_int, mask_int = cidr_to_ip_and_mask(ip_cidr)
                    args["ipv4_dst_addr"] = [ip_int, mask_int]
            #TODO: implement the other operands
            # TODO: implement other fields for the KEY

        return PreFilterKeys(instr_name='set_pkt_id',kwargs=args)
        # return [{"instr": "set_pkt_id", "kwargs": args}]

    @staticmethod
    def translate_default_action_to_micro(prefilter: PreFilterNode, manifest, pid) -> DefaultAction:
        """
        Translate a default action (like FWD, DROP, FWD_AND_ENQUEUE) 
        into a list of micro-instructions ready for installation.
        """
        default_action = prefilter.default_action

        instr = ""
        kwargs = ""

        if isinstance(default_action, DropInstr):
            # Drop action
            instr = "drop"
            kwargs = {
                    "pkt_id": 0,
                    # "port": 0,  # or None if not used by drop()
                    "program_id": pid
                }

        elif isinstance(default_action, FwdInstr):
            # Forward to a specific port
            dest = default_action.port
            front_port = get_pnum_from_endpoints(manifest, dest)
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)

            instr = "fwd"
            kwargs = {
                    "pkt_id": 0,
                    "port": dev_port,
                    "program_id": pid
                }

        elif isinstance(default_action, FwdAndEnqueueInstr):
            # Forward and enqueue to queue
            dest = default_action.target
            qid = default_action.qid
            front_port = get_pnum_from_endpoints(manifest, dest)
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)

            instr = "fwd_and_enqueue"
            kwargs = {
                    "pkt_id": 0,
                    "program_id": pid,
                    "port": dev_port,
                    "qid": qid
                }
            # return [{
            #     "instr": "fwd_and_enqueue",
            #     "kwargs": {
            #         "pkt_id": 0,
            #         "program_id": pid,
            #         "port": dev_port,
            #         "qid": qid
            #     }
            # }]

        else:
            raise ValueError(f"Unknown default action: {type(default_action)}")
        
        return DefaultAction(instr_name=instr, kwargs=kwargs)

    @staticmethod
    def translate_instr_to_micro(instr:InstructionNode, manifest, pid) -> List[MicroInstruction]:
        headers = {
            'IPV4.TTL': HEADER_IPV4_TTL,
            'IPV4.DST': HEADER_IPV4_DST,
            'IPV4.SRC': HEADER_IPV4_SRC,
            'TCP.ACK_NO': HEADER_TCP_ACK_NO,
            'TCP.SEQ_NO': HEADER_TCP_SEQ_NO,
            'TCP.FLAGS': HEADER_TCP_FLAGS,
            'IPV4.ID': HEADER_IPV4_IDENTIFICATION,
        }

        if isinstance(instr, FwdInstr):
            front_port = get_pnum_from_endpoints(manifest, instr["args"]["dest"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0) 
            # return [{"instr": "fwd_ni", "kwargs":{"port": dev_port, "program_id": pid}}]
            return [MicroInstruction(instr_name='fwd_ni', kwargs={"port": dev_port, "program_id": pid})]
        
        elif isinstance(instr, FwdAndEnqueueInstr):
            front_port = get_pnum_from_endpoints(manifest, instr["args"]["dest"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0) 
            # return [{"instr": "fwd_ni", "kwargs":{"port": dev_port, "program_id": pid}}]
            return [MicroInstruction(instr_name='fwd_ni', kwargs={"port": dev_port, "program_id": pid, "qid": instr.qid})]
        
        elif isinstance(instr, HeaderIncrementInstr):
            # sum_ni(ni=current_instr, pkt_id=[pkt_id, MASK_PKT_ID], instr_id=next_instruct, header_update=1, header_id=HEADER_IPV4_TTL, const_val=1)
            if instr['args']['target'] == "IPV4.TTL":
                return [
                    MicroInstruction(instr_name='fetch_ipv4_ttl', kwargs={}),
                    MicroInstruction(instr_name='sum_ni', kwargs={"program_id": pid, "header_update":1, "header_id": HEADER_IPV4_TTL, "const_val": instr['args']['value']}),
                        ]
        
        elif isinstance(instr, HeaderAssignInstr):
            tofino_header = headers[instr['args']['target']]            
            return [
                MicroInstruction(instr_name='sum_ni', kwargs={"program_id": pid, "header_update":1, "header_id": tofino_header, "const_val": instr['args']['value']}),
                    ]
        
        raise MicroInstructionError(f"Unsupported micro instruction '{type(instr).__name__} of type {type(instr)}'")

    @classmethod
    def translate_body_to_micro(self, prefilter:PreFilterNode, manifest, pid):
        micro_instrs = []
        for instr in prefilter.body.instructions:
            micro_instrs.extend(self.translate_instr_to_micro(instr, manifest, pid))
        return micro_instrs

    # @classmethod
    # def to_micro(self, program, manifest, pid) -> StageRunMicroProgram:
    #     stagerun_micro_program = StageRunMicroProgram(program['program'])

    #     for prefilter in program['prefilters']:

    #         name = prefilter['name']
    #         keys = self.translate_keys_to_micro(prefilter, manifest, pid)
    #         action = self.translate_default_action_to_micro(prefilter, manifest, pid)

    #         # print("To_micro ACTION:")
    #         # print(action.instr_name)
    #         # print(action.kwargs)
    #         body = self.translate_body_to_micro(prefilter, manifest, pid)

    #         pf = PreFilter(name, keys, action, body)
            
    #         stagerun_micro_program.prefilters.append(pf)

    #     return stagerun_micro_program

    @classmethod
    def to_micro(self, program:ProgramNode, manifest:json, pid:int) -> StageRunMicroProgram:
        name=""
        prefilters, ports_in, ports_out, qsets = [], [], [], []

        for prefilter in program.prefilters:

            name = prefilter.name
            keys = self.translate_keys_to_micro(prefilter, manifest, pid)
            action = self.translate_default_action_to_micro(prefilter, manifest, pid)

            # print("To_micro ACTION:")
            # print(action.instr_name)
            # print(action.kwargs)
            body = self.translate_body_to_micro(prefilter, manifest, pid)

            prefilters.append(PreFilter(name, keys, action, body))
        
        for port in program.ports_in:
            ports_in.append(InPort(port.name)) 
        for port in program.ports_out:
            ports_out.append(OutPort(port.name, port.qset)) 
        for qset in program.qsets:
            qsets.append(Qset(name=qset.name,
                                 type=qset.type,
                                 size=qset.size)) 

        return StageRunMicroProgram(
            name=name,
            prefilters=prefilters,
            ports_in=ports_in,
            ports_out=ports_out,
            qsets=qsets
        )
