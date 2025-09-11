from lib.tofino.types import *
from lib.tofino.constants import *
from lib.engine.mechanisms.write_phase_mechanism import WritePhaseMechanism

# class ProgramIdMechanismKeys(BaseTableKeys):
#     def __init__(self, f1_next_instr=[0,0], f2_next_instr=[0,0], ig_port=[0,0], original_ig_port=[0,0]):
#         super().__init__()
#         self.f1_next_instr=f1_next_instr
#         self.f2_next_instr=f2_next_instr
#         self.ig_port=ig_port
#         self.original_ig_port=original_ig_port

#     def to_key_list(self):
#         """
#         Converts the key values to the format required by the runtime.
#         """

#         # self.annotations = [["hdr.ipv4.dstAddr", "ipv4"], ["hdr.ipv4.srcAddr", "ipv4"]]
#         return [
#             ["hdr.bridge_meta.f1.next_instruction",     self.f1_next_instr[0],     self.f1_next_instr[1],       "ternary"],
#             ["hdr.bridge_meta.f2.next_instruction",     self.f2_next_instr[0],     self.f2_next_instr[1],       "ternary"],
#             ["ig_intr_md.ingress_port",                 self.ig_port[0],           self.ig_port[1],             "ternary"],
#             ["hdr.bridge_meta.original_ingress_port",   self.original_ig_port[0],  self.original_ig_port[1],    "ternary"],
#         ]


# class ProgramIdMechanism(BaseTable):

#     def __init__(self, runtime, location):
#         super().__init__(runtime, f"{location}.initblock.is_program_enabled_t")
    
#     # Action implementations
#     def add_program(self, f1_next_instr=[0,0], f2_next_instr=[0,0], ig_port=[0,0], original_ig_port=[0,0], pid=1):
#         keys = ProgramIdMechanismKeys(f1_next_instr, f2_next_instr, ig_port, original_ig_port)
#         action = BaseAction("set_program_enabled", pid)
#         self.add_entry(keys, action)

class PortMetadataKeys(BaseTableKeys):

    def __init__(self, ig_port):
        super().__init__()
        self.ig_port = ig_port 
           
    def to_key_list(self):

        return [
            ["ig_intr_md.ingress_port", self.ig_port, "exact"],
        ]


class PortMetadataMechanism(BaseTable):
    def __init__(self, runtime):
        super().__init__(runtime, "$PORT_METADATA")

    def add_data(self, ig_port=0, hash_constant=0, program_id=1):
        
        keys = PortMetadataKeys(ig_port)
        action = BaseAction("")
        action.action_params = {
            "action_name": "",
            "params": {
                "field1": hash_constant,
                "field2": 0,
                "field3": 0,
                "program_id": program_id,
            }
        }
        self.add_entry(keys, action)

    def clear(self):
        self.clear_table()


class PortMetadataMechanismManager(BaseTable):

    def __init__(self, runtime, write_phase_mechanism: WritePhaseMechanism, port_metadata_mechanism: PortMetadataMechanism):
        super().__init__(runtime, "$PORT_METADATA")
        self.programs = {}
        self.write_phase_mechanism = write_phase_mechanism
        self.port_metadata_mechanism = port_metadata_mechanism
        
    # Action implementations
    def add_program(self, program:Program):
        self.programs[program.pid] = program

    # Set Program makes the program_id goes into the $PORT_METADATA of each port
    def set_program(self, pid=1):
        if pid in self.programs:
            program = self.programs[pid]

            self.write_phase_mechanism.set_write_phases(program_id=pid, write_s3=program.wp_s3, write_s4=program.wp_s4, write_s5=program.wp_s5, write_s6=program.wp_s6, write_s7=program.wp_s7, write_s8=program.wp_s8, write_s9=program.wp_s9, write_s10=program.wp_s10)

            self.port_metadata_mechanism.clear()
            for port in program.ports:
                self.port_metadata_mechanism.add_data(ig_port=port, program_id=pid)
            
            print(f"[✓] Program switched to {program.name}")
        else:
            print(f"Program {pid} not present in program's installed list")

    def show_programs(self):
        for p in self.programs.values():
            print(f"Program {p.pid} => '{p.name}'")
