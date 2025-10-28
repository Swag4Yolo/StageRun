import ipaddress

from lib.controller.deployer.types import *
from lib.controller.constants import *
from lib.tofino.constants import *
from lib.utils.manifest_parser import get_pnum_from_endpoints
import lib.controller.state_manager as sm



def cidr_to_ip_and_mask(ip_cidr: str):
    """Converts CIDR (e.g. '10.10.1.0/24') to (ip_int, mask_int)."""
    network = ipaddress.IPv4Network(ip_cidr, strict=False)
    ip_int = int(network.network_address)
    mask_int = int(network.netmask)
    return ip_int, mask_int


class MicroInstructionParser():

    def __init__(self):
        pass

    @staticmethod
    def translate_keys_to_micro(prefilter, manifest, pid) -> PreFilterKeys:
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
        for key in prefilter["keys"]:
            field = key["field"]
            value = key["value"]

            if field == "PKT.PORT":
                port = get_pnum_from_endpoints(manifest, value)
                dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(port, 0)
                args["ig_port"] = [dev_port, MASK_PORT]

            elif field == "IPV4.DST":
                ip_cidr = value  # e.g. "10.10.1.0/24"
                ip_int, mask_int = cidr_to_ip_and_mask(ip_cidr)
                args["ipv4_dst_addr"] = [ip_int, mask_int]


            # Podes ir adicionando outros campos (SRC, TCP ports, etc.)

        return PreFilterKeys(instr_name='set_pkt_id',kwargs=args)
        # return [{"instr": "set_pkt_id", "kwargs": args}]

    @staticmethod
    def translate_default_action_to_micro(prefilter, manifest, pid) -> DefaultAction:
        """
        Translate a default action (like FWD, DROP, FWD_AND_ENQUEUE) 
        into a list of micro-instructions ready for installation.
        """
        default_action = prefilter['default']
        op = default_action["op"].upper()
        args = default_action.get("args", {})

        instr = ""
        kwargs = ""

        if op == "DROP":
            # Drop action

            instr = "drop"
            kwargs = {
                    "pkt_id": 0,
                    # "port": 0,  # or None if not used by drop()
                    "program_id": pid
                }

        elif op == "FWD":
            # Forward to a specific port
            dest = args.get("dest")
            front_port = get_pnum_from_endpoints(manifest, dest)
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)

            instr = "fwd"
            kwargs = {
                    "pkt_id": 0,
                    "port": dev_port,
                    "program_id": pid
                }

        elif op in ("FWD_ENQUEUE", "FWD_AND_ENQUEUE"):
            # Forward and enqueue to queue
            dest = args.get("dest")
            qid = args.get("qid", 0)
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
            raise ValueError(f"Unknown default action: {op}")
        
        return DefaultAction(instr_name=instr, kwargs=kwargs)

    @staticmethod
    def translate_instr_to_micro(instr, manifest, pid) -> List[MicroInstruction]:
        headers = {
            'IPV4.TTL': HEADER_IPV4_TTL,
            'IPV4.DST': HEADER_IPV4_DST,
            'IPV4.SRC': HEADER_IPV4_SRC,
            'TCP.ACK_NO': HEADER_TCP_ACK_NO,
            'TCP.SEQ_NO': HEADER_TCP_SEQ_NO,
            'TCP.FLAGS': HEADER_TCP_FLAGS,
            'IPV4.ID': HEADER_IPV4_IDENTIFICATION,
        }

        if instr['op'] == FWD:
            front_port = get_pnum_from_endpoints(manifest, instr["args"]["dest"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0) 
            # return [{"instr": "fwd_ni", "kwargs":{"port": dev_port, "program_id": pid}}]
            return [MicroInstruction(instr_name='fwd_ni', kwargs={"port": dev_port, "program_id": pid})]
        
        elif instr['op'] == HINC:
            # sum_ni(ni=current_instr, pkt_id=[pkt_id, MASK_PKT_ID], instr_id=next_instruct, header_update=1, header_id=HEADER_IPV4_TTL, const_val=1)
            if instr['args']['target'] == "IPV4.TTL":
                return [
                    MicroInstruction(instr_name='fetch_ipv4_ttl', kwargs={}),
                    MicroInstruction(instr_name='sum_ni', kwargs={"program_id": pid, "header_update":1, "header_id": HEADER_IPV4_TTL, "const_val": instr['args']['value']}),
                        ]
        
        elif instr['op'] == ASSIGNMENT:
            tofino_header = headers[instr['args']['target']]            
            return [
                MicroInstruction(instr_name='sum_ni', kwargs={"program_id": pid, "header_update":1, "header_id": tofino_header, "const_val": instr['args']['value']}),
                    ]

    @classmethod
    def translate_body_to_micro(self, prefilter, manifest, pid):
        micro_instrs = []
        for instr in prefilter['body']:
            micro_instrs.extend(self.translate_instr_to_micro(instr, manifest, pid))
        return micro_instrs

    @classmethod
    def to_micro(self, program, manifest, pid) -> StageRunMicroProgram:
        stagerun_micro_program = StageRunMicroProgram(program['program'])

        for prefilter in program['prefilters']:

            name = prefilter['name']
            keys = self.translate_keys_to_micro(prefilter, manifest, pid)
            action = self.translate_default_action_to_micro(prefilter, manifest, pid)

            # print("To_micro ACTION:")
            # print(action.instr_name)
            # print(action.kwargs)
            body = self.translate_body_to_micro(prefilter, manifest, pid)

            pf = PreFilter(name, keys, action, body)
            
            stagerun_micro_program.prefilters.append(pf)

        return stagerun_micro_program
