from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any
from .planner import PlanningResult
from .types import MicroNode
import lib.controller.state_manager as sm
from lib.controller.constants import P1_TABLE, P2_TABLE, SPEC_TABLE
from lib.tofino.constants import *
import logging

logger = logging.getLogger(__name__)


@dataclass
class Installer:

    @staticmethod
    def install_prefilter_keys(keys:dict = {}):
        """
        Install the prefilter key in hardware.
        """

        if keys and "instr" in keys and "kwargs" in keys:
            instr = keys["instr"]
            kwargs = keys["kwargs"]

            # Choose table
            table_to_install_rule = sm.engine_controller.pre_filter_mechanism

            func = getattr(table_to_install_rule, instr, None)
            if func is None:
                raise RuntimeError(f"Instruction {instr} does not exist in PreFilter Mechanism (key installation).")
        if __debug__:
            logger.debug("install_prefilter_keys:")
            logger.debug(f"func:{func}\nkwargs:{kwargs}")

        if kwargs:
            func(**kwargs)

    @staticmethod
    def install_default_action(default_action:dict = {}):
        """
        Installs the default action for the prefilter (drop, fwd, fwd_and_enqueue).
        """
        func = None
        kwargs = None
        if default_action and "instr" in default_action and "kwargs" in default_action:
            instr = default_action["instr"]
            kwargs = default_action["kwargs"]

            func = getattr(sm.engine_controller.generic_fwd, instr, None)
            if func is None:
                raise RuntimeError(f"Instruction {instr} does not exist in PreFilter Mechanism (key installation).")
        if __debug__:
            logger.debug("install_default_action:")
            logger.debug(f"func:{func}\nkwargs:{kwargs}")
            
        if kwargs:
            func(**kwargs)

    @staticmethod
    def install_node(node: MicroNode):
        
        table = node.allocated_table
        table_to_install_rule = None

        if node.instr.name == "decide":
            #TODO: implement conditionals
            return

        elif node.instr.name == "pos_filter_recirc_same_pipe" or table == "recirculation_t":
            func = getattr(sm.engine_controller.pos_filter_mechansim, "pos_filter_recirc_same_pipe", None)

            kwargs = {
                "program_id": [node.instr.kwargs["program_id"], MASK_PROGRAM_ID], 
                "f1_next_instr": [node.instr.kwargs["flow_id"], MASK_FLOW], 
                "next_flow_id": node.instr.kwargs["next_flow"]}

        elif node.instr.name == "configure_write_phase" or table == "write_phase_t":
            return

            func = getattr(sm.engine_controller.write_phase_mechanism, "set_write_phases", None)

            kwargs = {
                "program_id" : getattr(node.instr.kwargs, "program_id", 1),
                "write_s3"   : getattr(node.instr.kwargs, "write_s3", 0), 
                "write_s4"   : getattr(node.instr.kwargs, "write_s4", 0), 
                "write_s5"   : getattr(node.instr.kwargs, "write_s5", 0), 
                "write_s6"   : getattr(node.instr.kwargs, "write_s6", 0),
                "write_s7"   : getattr(node.instr.kwargs, "write_s7", 0),
                "write_s8"   : getattr(node.instr.kwargs, "write_s8", 0), 
                "write_s9"   : getattr(node.instr.kwargs, "write_s9", 0), 
                "write_s10"  : getattr(node.instr.kwargs, "write_s10", 0),
            }

        elif table in P1_TABLE:
            table_to_install_rule = sm.engine_controller.p1_table
        elif table in P2_TABLE:
            table_to_install_rule = sm.engine_controller.p2_table
        elif table in SPEC_TABLE:
            table_to_install_rule = sm.engine_controller.spec_table

        if table_to_install_rule:
            table_to_install_rule._set_location_(f"SwitchIngress.{node.allocated_flow}_i{node.allocated_stage}")
            
            # call method by name
            func = getattr(table_to_install_rule, node.instr.name, None)
            kwargs = node.instr.kwargs
            kwargs["ni"] = node.flow_id
            if func is None:
                raise RuntimeError(f"Instrução {node.micro_instr.instr_name} não existe no objeto {table_to_install_rule}")
        # Execute with the arguments
        if __debug__:
            logger.debug("install_node:")
            logger.debug(f"func:{func}\nkwargs:{kwargs}")

        if kwargs:
            func(**kwargs)

        if table_to_install_rule:
            table_to_install_rule.print_entries_for_pid(kwargs['program_id'])
        
    @classmethod
    def install_write_phases(self, wp_reserved: Dict[int, int], pid:int):
        func = getattr(sm.engine_controller.write_phase_mechanism, "set_write_phases", None)

        kwargs = {
            "program_id" : pid,
            "write_s3"   : wp_reserved.get(3, 0),
            "write_s4"   : wp_reserved.get(4, 0),
            "write_s5"   : wp_reserved.get(5, 0),
            "write_s6"   : wp_reserved.get(6, 0),
            "write_s7"   : wp_reserved.get(7, 0),
            "write_s8"   : wp_reserved.get(8, 0),
            "write_s9"   : wp_reserved.get(9, 0),
            "write_s10"  : wp_reserved.get(10, 0),
        }

        if __debug__:
            logger.debug("install_write_phases:")
            logger.debug(f"wp_reserved: {wp_reserved}")
            logger.debug(f"func:{func}\nkwargs:{kwargs}")

        func(**kwargs)
        

    @classmethod
    def install(self, plan: PlanningResult, pid: int):
        """
        Install the program graphs onto the switch.

        Each ControlFlowGraph corresponds to a PreFilter in the micro_program.
        The association is made via matching names (cfg.name == prefilter.name).
        """
        for g in plan.graphs:
            # 1. Keys
            self.install_prefilter_keys(g.keys)
            #2. Default Action
            self.install_default_action(g.default_action)
            # 3. Body
            for node in g.nodes.values():
                self.install_node(node)

        # 4. Install WP
        self.install_write_phases(plan.stats.wp_reserved, pid)