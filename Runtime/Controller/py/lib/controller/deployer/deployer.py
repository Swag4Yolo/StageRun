from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

import traceback
import os
# Custom Imports
from lib.controller.deployer.types import *
from lib.controller.deployer.micro_instruction import *
from lib.utils.utils import Timer

from Core.stagerun_graph.importer import load_stage_run_graphs  # lê JSON do compilador (com checksum)
from .micro_instruction import MicroInstructionParser
from .planner import Planner, PlanningResult   # implementas o MVP acima
# from .installer import install_plan # já tens base para instalar tables
# from .resources import apply_resources, cleanup_resources


timer = Timer()

def check_instruction_in_stage(pipeline, micro_instr, stage):
    stages_tables = pipeline[stage]

    for table in stages_tables:
        # print("Table")
        # print(table)
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
        
        # print("Table detected")
        # print(table)
        # print("stage_number")
        # print(stage_num)
        # print("instruction_num")
        # print(instruction_num)

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
	



# ---------------------------------------------------------------------------
# Utils de IO
# ---------------------------------------------------------------------------
def load_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)

def load_compiled_program(compiled_path: str | Path) -> Dict[str, Any]:
    """
    Lê o JSON produzido pelo compilador (exporter), contendo os StageRunGraphs.
    Espera um dicionário com pelo menos: {"graphs": [...], ...}
    """
    payload = load_json(compiled_path)
    # Se tiveres um importer dedicado, poderias usar:
    # graphs = import_stage_run_graphs_from_json(payload)
    # return {"graphs": graphs, "meta": { ... }}
    return payload

# ---------------------------------------------------------------------------
# Serialização leve do plan_result (só para logging / debug)
# ---------------------------------------------------------------------------
def plan_result_to_dict(plan_result: PlanningResult) -> Dict[str, Any]:
    """
    Converte o retorno do Planner para um dicionário serializável em JSON
    (sem perder infos úteis para debugging).
    """
    def node_to_dict(n: MicroNode) -> Dict[str, Any]:
        # n.instr tem (instr, kwargs)
        instr_name = getattr(n.instr, "instr", None)
        kwargs = getattr(n.instr, "kwargs", {}) or {}
        return {
            "id": n.id,
            "instr": instr_name,
            "kwargs": kwargs,
            "allocated_stage": getattr(n, "allocated_stage", None),
            "allocated_flow": getattr(n, "allocated_flow", None),
            "flow_id": getattr(n, "flow_id", None),
            "parent_node_id": getattr(n, "parent_node_id", None),
            "graph_id": getattr(n, "graph_id", None),
            "var_slot_map": getattr(g, "var_slot_map", {}),
            # "nodes": [...],

        }

    def edge_to_dict(e: MicroEdge) -> Dict[str, Any]:
        return {"src": e.src, "dst": e.dst, "dep": e.dep}

    graphs_out: List[Dict[str, Any]] = []
    for g in plan_result.graphs:
        graphs_out.append({
            "graph_id": g.graph_id,
            "keys" : g.keys,
            "default_action": g.default_action,
            "nodes": [node_to_dict(n) for n in g.nodes.values()],
            "edges": [edge_to_dict(e) for e in g.edges],
            # ChoiceGroups normalmente são resolvidos no Planner; se ainda houver, serializa:
        })
    stats = getattr(plan_result, "stats", None)
    stats_out = {
        "stages_used": getattr(stats, "stages_used", None),
        "total_nodes": getattr(stats, "total_nodes", None),
        "total_flows": getattr(stats, "total_flows", None),
        "write_phases_inserted": list(getattr(stats, "write_phases_inserted", None)),
        "write_phases": list(getattr(stats, "wp_reserved", None)),
    } if stats else None

    return {"graphs": graphs_out, "stats": stats_out}


# ------------------------------------------------------
def deploy_program(
    compiled_app: str,
    manifest: str,
    app_key: str,
    engine_key:str,
    program_id: int,
    *,
    deploy_hw: bool = True,
    return_dict: bool = False,
    pretty_print: bool = True,
) -> Dict[str, Any] | None:
    """
    1) Lê o JSON do compilador (StageRun graphs)
    2) Constrói MicroGraphs via MicroInstructionParser.to_micro()
    3) Corre o Planner para obter plan_result
    4) Devolve (ou imprime) um dicionário com o plano (sem instalar nada)
    """

    # try: 
    sm.connect_tofino()
    print("Inside Deploy Program")

    # compiled_app = load_compiled_program(compiled_json_path)
    # manifest = load_json(manifest_path)
    isa = sm.get_engine_ISA(sm.get_running_engine_key())

    stage_run_graphs = compiled_app.get("graphs", [])
    if not stage_run_graphs:
        raise ValueError("Compiled program JSON has no 'graphs' entry.")

    # 2) StageRun → Micro
    mip = MicroInstructionParser(isa=isa, manifest=manifest)
    micro_graphs: List[MicroGraph] = mip.to_micro(stage_run_graphs)

    if __debug__:
        with open("MicroGraphs.log", "w") as f:
            pass
        with open("MicroGraphsPlanned.log", "w") as f:
            pass
        for mg in micro_graphs:
            mg.debug_print()

    # 3) Planner
    planner = Planner(isa=isa)
    plan_result = planner.plan(micro_graphs, pid=program_id)

    if __debug__:
        for mg in plan_result.graphs:
            mg.debug_print(show_effects=True, filepath="MicroGraphsPlanned.log")

    # 4) Serializar para debug / output
    plan_dict = plan_result_to_dict(plan_result)

    if pretty_print:
        with open("deployer.log.json", "w") as f:
            f.write(json.dumps(plan_dict, indent=2, ensure_ascii=False))

    # 5. Configure resources
    resources = compiled_app["resources"]
    # TOO: save state regarding queues so that when the program runs it installs the necessary queues 
    # "resources" : {
    #    "queues": {
    #     "prio_queues": {
    #       "type": "PRIO",
    #       "size": 2,
    #       "ports": [
    #         "P1_OUT",
    #         "P2_OUT"
    #       ]
    #     },
    #     "rr_queues": {
    #       "type": "RR",
    #       "size": 2,
    #       "ports": [
    #         "PRR_OUT"
    #       ]
    #     }
    #   }
    # }

    return False, "NotImplementedError: Installer is still being developed"
    # return plan_dict if return_dict else None

def deploy_program_old(compiled_app, manifest, app_key, engine_key, program_id, target_hw=True):

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
        timer.start()
        cfg_graphs = CFGBuilder.build(stagerun_micro_program)
        timer.finish()
        timer.calc("ControlFlowGraph =>")

        # 3. Planning Phase
        timer.start()
        cfg_graphs = Planner.plan(stagerun_micro_program, cfg_graphs)
        timer.finish()
        timer.calc("Planner Phase =>")

        # 4. Install
        timer.start()
        Installer.install(stagerun_micro_program, cfg_graphs)
        timer.finish()
        timer.calc("Install Phase =>")
        
        sm.engine_controller.write_phase_mechanism.set_write_phases(program_id=program_id, write_s10=1)

        return True, ""
    
    except Exception as e:
        print(traceback.format_exc())
        return False, f"Failed to Deploy Application in the Engine. {repr(e)}"
