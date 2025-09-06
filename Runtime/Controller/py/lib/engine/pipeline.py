from lib.tofino.runtime import *
from lib.tofino.types import *

from lib.engine.instructions.instruction_tables import *
from lib.engine.mechanisms.pre_filter_mechanism import *
from lib.engine.mechanisms.cloning_mechanism import *
from lib.engine.mechanisms.write_phase_mechanism import *
from lib.engine.mechanisms.program_enabler_mechanism import *
from lib.engine.mechanisms.pattern_mechanism import *
from lib.engine.mechanisms.pos_filter_mechanism import *
from lib.engine.mechanisms.port_mechanism import *
from lib.engine.mechanisms.hash_mechanism import *
from lib.engine.mechanisms.random_mechanism import *
from lib.engine.mechanisms.write_phase_conditional_mechanism_after_reg import *
from lib.engine.mechanisms.program_id_mechanism import *


from lib.engine.configurations.padding_configuration import *
from lib.engine.configurations.write_phase_configuration import *
# from lib.utils.manifest_parser import PortInfo, SwitchInfo

from time import sleep

class BRIFlow():
    def __init__(self, bfrt_runtime:bfrt_runtime, flow_number: int):
        self.runtime = bfrt_runtime
        # self.flow_number = flow_number


        #Instructions
        self.i1_p1 = P1Table(self.runtime, f"SwitchIngress.f{flow_number}_i1")
        self.i1_p2 = InstructPackInit_P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i1")
        self.i1_speculative = InstructPackInitSpeculative(self.runtime, f"SwitchIngress.f{flow_number}_i1")
        self.i2_p2 = P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i2")
        self.i2_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i2")
        self.i3_p2 = InstructPack3_P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i3")
        self.i3_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i3")
        self.i4_p2 = InstructPack6_P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i4")
        self.i4_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i4")
        self.i5_p2 = InstructPack5_P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i5")
        self.i5_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i5")
        self.i6_p2 = P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i6")
        self.i6_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i6")
        self.i7_p2 = P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i7")
        self.i7_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i7")

        if flow_number == 2:
            self.i8_p2 = P2Table(self.runtime, f"SwitchIngress.f{flow_number}_i8")
            self.i8_speculative = Speculative(self.runtime, f"SwitchIngress.f{flow_number}_i8")
        else:            
            self.i8_multi = MultiInstructionLastStage(self.runtime, f"SwitchIngress.f{flow_number}_i8")

        self.i9_multi = MultiInstructionLastStage(self.runtime, f"SwitchIngress.f{flow_number}_i9")


class BRIWritePhase():
    def __init__(self, bfrt_runtime:bfrt_runtime, location):
        self.runtime = bfrt_runtime
        self.location = location
        
        self.conditional_mechanism_after_reg = WritePhaseConditionalMechanismAfterReg(self.runtime, self.location)

class BRIPipeline():
    def __init__(self, bfrt_runtime:bfrt_runtime):
        self.runtime = bfrt_runtime
        self.location = "SwitchIngress"
        
        #Flows
        self.f1 = BRIFlow(self.runtime, 1)
        self.f2 = BRIFlow(self.runtime, 2)

        #Write Phases
        self.wp_s3 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s3')
        self.wp_s4 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s4')
        self.wp_s5 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s5')
        self.wp_s6 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s6')
        self.wp_s7 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s7')
        self.wp_s8 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s8')
        self.wp_s9 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s9') #TODO: s9 can have two conditionals; whereas others don't
        # self.wp_s10 = BRIWritePhase(self.runtime, f'{self.location}.write_phase_s10')

        #Mechanisms
        self.pre_filter_mechanism = PreFilterMechanism(self.runtime, f"{self.location}")
        self.generic_fwd = GenericFwd(self.runtime, f"{self.location}")
        self.clone_mechanism = CloneMechanism(self.runtime)
        self.write_phase_mechanism = WritePhaseMechanism(self.runtime, self.location)
        self.program_enabler_mechanism = ProgramEnablerMechanism(self.runtime, self.location)
        self.pattern_mechanism = PatternMechanism(self.runtime, self.location)
        self.pos_filter_mechansim = PosFilterMechanism(self.runtime, self.location)
        self.port_mechanism = PortMechanism(self.runtime)
        self.hash_mechanism = [HashMechanism(self.runtime, self.location + '.initblock.hash_1'), HashMechanism(self.runtime, self.location + '.initblock.hash_2'), HashMechanism(self.runtime, self.location + '.initblock.hash_3')]
        self.random_mechanism = RandomMechanism(self.runtime, self.location)
        self.port_metadata_mechanism = PortMetadataMechanism(self.runtime)
        
        # Port Metadata Mechanism Manager
        # Currently responsible for program_id, hash_constant
        self.program_id_mechanism = PortMetadataMechanismManager(self.runtime, self.write_phase_mechanism, self.port_metadata_mechanism)

    def _init_configs_(self):
        PaddingInitModes(self.runtime, self.location)
        CalculatePadding(self.runtime, self.location)
        PosFilterMechanism(self.runtime, self.location)._begin_rules()



        # for p_info in self.switch_info.ports:
            # print ("Pinfo speed", p_info.speed)
            # print ("Pinfo loopback", p_info.loopback)
            # print ("Pinfo.p_num", p_info.p_num)
            
            # print ("pnum is an int") if isinstance(p_info.p_num, int) else None

            # p_info = PortInfo(p_info)

        #     speed = PORT_SPEED_BF[p_info.speed]
        #     loopback = PORT_LOOPBACK_BF[p_info.loopback]
        #     fec = PORT_FEC_BF.get( (speed, loopback), FEC_NONE)
        #     self.port_mechanism.add_port(front_port=p_info.p_num, speed=speed, loopback=loopback, fec=fec)


        # if len(self.switch_info.ports) > 1:
        #     print("Waiting for ports to become up")
        #     sleep(3)
        #     print("Ports added successfully")


        # ### Imported from manifest
        # #TODO: import from manifest
        # """
        #     49/0 |20/0|156|3/28|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |               2|               0|
        #     50/0 |22/0|140|3/12|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |         1873280|         1873390|
        #     51/0 |16/0|188|3/60|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |               0|         1873744|
        #     52/0 |18/0|172|3/44|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |         1873981|               0|
        #     53/0 |12/0| 32|0/32|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |         6819749|               0|
        #     54/0 |14/0| 48|0/48|100G   | RS |Au|Au|YES|ENB|DWN|  NONE  |               0|               0|
        #     55/0 | 9/0|  8|0/ 8|100G   | RS |Au|Au|YES|ENB|UP |  NONE  |               0|         6822680|
        #     56/0 |10/0| 16|0/16|100G   | RS |Au|Au|YES|ENB|DWN|  NONE  |               0|               0|
        #     57/0 |32/0| 64|0/64|100G   |NONE|Au|Au|YES|ENB|UP |Mac-near|               0|               0|
        # """
        # self.port_mechanism.add_port(49)
        # self.port_mechanism.add_port(50)
        # # self.port_mechanism.add_port(51)
        # self.port_mechanism.add_port(front_port=51, fec=FEC_NONE, loopback=LOOPBACK_MAC_NEAR)
        # # self.port_mechanism.add_port(52)
        # self.port_mechanism.add_port(front_port=52, fec=FEC_NONE, loopback=LOOPBACK_MAC_NEAR)
        # # self.port_mechanism.add_port(53)
        # self.port_mechanism.add_port(front_port=53, fec=FEC_NONE, loopback=LOOPBACK_MAC_NEAR)
        # self.port_mechanism.add_port(54)
        # # self.port_mechanism.add_port(55)
        # self.port_mechanism.add_port(front_port=55, fec=FEC_NONE, loopback=LOOPBACK_MAC_NEAR)
        # self.port_mechanism.add_port(56)
        # self.port_mechanism.add_port(front_port=57, fec=FEC_NONE, loopback=LOOPBACK_MAC_NEAR)

        #bfrt_hw
        for i in range(3, 11):
            ToFwd(self.runtime, self.location, i)
            ExternalVar(self.runtime, self.location, i)
            Var1Var3(self.runtime, self.location, i)
            Var2Var4(self.runtime, self.location, i)
            if i == FINAL_STAGE:
                HeaderWrite(self.runtime, self.location, i, True)
            else:
                HeaderWrite(self.runtime, self.location, i)

            Activate(self.runtime, self.location, i)

    def _final_configs_(self):
        PosFilterMechanism(self.runtime, self.location)._last_rules()



