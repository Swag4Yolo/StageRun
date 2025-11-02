from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any


@dataclass
class Installer:

    @staticmethod
    def install_prefilter_key(prefilter: PreFilter, cf_id: int, cf_id_2: int, pkt_id: int):
        """
        Install the prefilter key in hardware.
        """
        keys = prefilter.keys
        instr = keys.instr_name
        kwargs = keys.kwargs

        # Attach identifiers
        kwargs["ni_f1"] = cf_id
        kwargs["ni_f2"] = cf_id_2
        kwargs["pkt_id"] = pkt_id


        # print("keys=",keys)

        # print("instr=",instr)
        # print("kwargs=",kwargs)


        # Choose table
        table_to_install_rule = sm.engine_controller.pre_filter_mechanism

        func = getattr(table_to_install_rule, instr, None)
        if func is None:
            raise RuntimeError(f"Instruction {instr} does not exist in PreFilter Mechanism (key installation).")

        func(**kwargs)

    @staticmethod
    def install_default_action(prefilter: PreFilter, pkt_id):
        """
        Installs the default action for the prefilter (drop, fwd, fwd_and_enqueue).
        """
        default = prefilter.default_action

        # print("Inside Install_default_action")
        # print(default)
        if (default):
            instr = default.instr_name
            kwargs = default.kwargs
            kwargs['pkt_id'] = pkt_id

            if instr not in ["drop", "fwd", "fwd_and_enqueue"]:
                raise RuntimeError(f"Default action '{instr}' not recognized.")

            func = getattr(sm.engine_controller.generic_fwd, instr, None)
            if func is None:
                raise RuntimeError(f"Instruction {instr} does not exist in PreFilter Mechanism (key installation).")

            func(**kwargs)

        # Call corresponding micro function
        # if instr == "drop":
        #     sm.engine_controller.generic_fwd.drop(**kwargs)
        # elif instr == "fwd":
        #     sm.engine_controller.generic_fwd.fwd(**kwargs)
        # elif instr == "fwd_and_enqueue":
        #     sm.engine_controller.generic_fwd.fwd_and_enqueue(**kwargs)

    @classmethod
    def install(self, micro_program: StageRunMicroProgram, cfg_graphs: Dict[str, ControlFlowGraph]):
        """
        Install the program graphs onto the switch.

        Each ControlFlowGraph corresponds to a PreFilter in the micro_program.
        The association is made via matching names (cfg.name == prefilter.name).
        """
        pkt_id = 1

        # Build a mapping of prefilter name -> object for fast lookup
        prefilter_map = {pf.name: pf for pf in micro_program.prefilters}

        for cfg_name, cfg in cfg_graphs.items():
            # Try to find the matching prefilter
            prefilter = prefilter_map.get(cfg_name)
            if prefilter is None:
                raise RuntimeError(f"No PreFilter found for CFG '{cfg_name}'")

            cf_id = cfg.initial_cf_id_f1
            cf_id_2 = cfg.initial_cf_id_f2

            # print("PrefilterName:")
            # print(cfg_name)

            # 1. Keys
            self.install_prefilter_key(prefilter, cf_id, cf_id_2, pkt_id)

            # 2. Default Action
            self.install_default_action(prefilter, pkt_id)

            # 3. Body
            for node in cfg.nodes:
                self.install_node(node)

            pkt_id += 1
