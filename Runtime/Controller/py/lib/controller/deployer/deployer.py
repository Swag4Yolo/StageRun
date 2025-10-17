import traceback
# import ipaddress

# Custom Imports
from lib.controller.deployer.types import *
from lib.controller.deployer.micro_instruction import *

# def cidr_to_range(ip_str, mask):
#     net = ipaddress.ip_network(f"{ip_str}/{mask}", strict=False)
#     return (int(net.network_address), int(net.broadcast_address))

def check_instruction_in_stage(pipeline, micro_instr, stage):
    stages_tables = pipeline[stage]

    for table in stages_tables:
        print("Table")
        print(table)
        if micro_instr['instr'] in stages_tables[table]:
            return table
    return None

	
def install_micro_instr(micro_instr, current_stage):
    pipeline = sm.get_engine_ISA(sm.get_running_engine_key())['pipeline']
    
    last_stage = current_stage
    current_stage_num = int(current_stage[1:])

    for stage_num in range(current_stage_num, 10):
        
        stage = f"s{stage_num}"
        instruction_num = stage_num - 1
        flow_number = 1

        table = check_instruction_in_stage(pipeline, micro_instr, stage)
        
        print("Table detected")
        print(table)
        print("stage_number")
        print(stage_num)
        print("instruction_num")
        print(instruction_num)

        if table:
            table_to_install_rule = None
            if table in P1_TABLE:
                table_to_install_rule = sm.engine_controller.p1_table
            elif table in P2_TABLE:
                table_to_install_rule = sm.engine_controller.p2_table
            elif table in SPEC_TABLE:
                table_to_install_rule = sm.engine_controller.spec_table

            # I want to run
            if table_to_install_rule:

                table_to_install_rule._set_location_(f"SwitchIngress.f{flow_number}_i{instruction_num}")
                
                # call method by name
                func = getattr(table_to_install_rule, micro_instr["instr"], None)
                if func is None:
                    raise RuntimeError(f"Instrução {micro_instr['instr']} não existe no objeto {table_to_install_rule}")
                
                args = micro_instr.get("args", [])
                kwargs = micro_instr.get("kwargs", {})


                # Execute with the arguments
                func(*args, **kwargs)
                return f"s{stage_num+1}"

    return None
	

#def generate_cfg(micro_program: StageRunProgram, manifest, program_id):


def deploy_program(compiled_app, manifest, app_key, engine_key, program_id, target_hw=True):

    try:
        sm.connect_tofino()

        # 1. Expand Phase - Translate Program to micro program
        stagerun_micro_program = MicroInstructionParser.to_micro(compiled_app, manifest, program_id)


        """
        [✓] Tofino Connection
        micro_program.prefilters:
        Name: 
            toRouterA
        Keys:
            {'instr': 'set_pkt_id', 'kwargs': {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.1.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}
        Default Action:
            [{'instr': 'fwd', 'kwargs': {'pkt_id': 0, 'port': 156, 'program_id': 1}}]
        Body:
            {'instr': 'fetch_ipv4_ttl', 'kwargs': {}}
            {'instr': 'sum_ni', 'kwargs': {'program_id': 1, 'header_update': 1, 'header_id': 1, 'const_val': 1}}

        Name:
            toRouterB
        Keys:
            {'instr': 'set_pkt_id', 'kwargs': {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.2.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}
        Default Action:
            [{'instr': 'fwd', 'kwargs': {'pkt_id': 0, 'port': 156, 'program_id': 1}}]
        Body:
            {'instr': 'fetch_ipv4_ttl', 'kwargs': {}}
            {'instr': 'sum_ni', 'kwargs': {'program_id': 1, 'header_update': 1, 'header_id': 1, 'const_val': -1}}
        Name:
            FromInternal
        Keys:
            {'instr': 'set_pkt_id', 'kwargs': {'ig_port': [156, 156], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': [0, 0], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}
        Default Action:
            [{'instr': 'fwd', 'kwargs': {'pkt_id': 0, 'port': 140, 'program_id': 1}}]
        Body:
            None
        """

        # 2. Control Flow Graph
        cfg_graphs = CFGBuilder.build(stagerun_micro_program)

        # 3. Planning Phase
        cfg_graphs = Planner.plan(stagerun_micro_program, cfg_graphs)

        # 4. Install
        Installer.install(stagerun_micro_program, cfg_graphs)

        # pipeline = sm.get_engine_ISA(sm.get_running_engine_key())['pipeline']
        # rules_to_install = planning_phase(cfg, pipeline)

        # install_rules_in_hw(rules_to_install)



        # print("micro_program")
        # print(micro_program)
        # stage = "s2"
        # for micro_instr in micro_program:
        #     stage = install_micro_instr(micro_instr, stage)
        #     if not stage:
        #         return False, f"Failed to allocate a stage sequence for the application."
        
        sm.engine_controller.write_phase_mechanism.set_write_phases(program_id=program_id, write_s10=1)

        return True, ""
    
    except Exception as e:
        print(traceback.format_exc())
        return False, f"Failed to Deploy Application in the Engine. {repr(e)}"
