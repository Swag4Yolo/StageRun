# Other Imports
import re
import logging

# StageRun Imports
import lib.controller.state_manager as sm
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from lib.controller.constants import *


class StageRunMicroProgram():
    def __init__(self, name = ""):
        # Parsing the IR (from the compiler)
        self.name = name
        self.prefilters = []
        self.posfilters = []

        # Generating the Graph
        # self.graphs: dict[str, ControlFlowGraph] = {}

    def show(self):
        for prefilter in self.prefilters:
            prefilter.show()


@dataclass
class PreFilterKeys:
    instr_name: str   # e.g. "set_pkt_id"
    kwargs: dict      # {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.1.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}

@dataclass
class DefaultAction:
    instr_name: str   # e.g. "set_pkt_id"
    kwargs: dict      # {'ig_port': [140, 140], 'original_ig_port': [0, 0], 'total_pkt_len': [0, 0], 'tcp_dst_port': [0, 0], 'ipv4_src_addr': [0, 0], 'ipv4_dst_addr': ['10.10.1.0', 24], 'tcp_flags': [0, 0], 'ipv4_proto': [0, 0], 'udp_sport': [0, 0], 'udp_dport': [0, 0], 'pkt_id': 0, 'ni_f1': 0, 'ni_f2': 0, 'program_id': 1}}

@dataclass
class MicroInstruction:
    instr_name: str   # sum_ni
    kwargs: dict      # {"program_id": pid, "header_update":1, "header_id": HEADER_IPV4_TTL, "const_val":instr['args']['value']}

@dataclass
class PreFilter:
    name: str
    keys: PreFilterKeys
    default_action: DefaultAction
    body: List[MicroInstruction]

    def show(self):
        print("Name:")
        print(self.name)

        print("Keys:")
        for key in self.keys:
            print(key)

        print("Default Action:")
        print(self.default_action)

        print("Body:")
        for instr in self.body:
            print(instr)



@dataclass
class CFGNode:
    id: int                          # globally unique ID (assigned by builder)
    micro_instr: MicroInstruction
    # instr_name: str                       # e.g. "sum_ni"
    # kwargs: dict                     # micro-instruction args
    deps: list[int] = field(default_factory=list)  # list of node IDs it depends on

    # Filled by the Allocator
    cf_id: int | None = None         # filled later by allocator
    allocated_stage: int | None = None  # filled later by allocator
    allocated_table: str | None = None
    allocated_flow: int | None = None

class ControlFlowGraph:
    """Represents the instruction dependencies of a single PreFilter body."""
    def __init__(self, name: str):
        self.name = name             # e.g. "toRouterA"
        self.nodes: list[CFGNode] = []
        self.initial_cf_id_f1 = None
        self.initial_cf_id_f2 = None

    def add_node(self, node: CFGNode):
        self.nodes.append(node)

class CFGBuilder:
    def __init__(self):
        pass
    
    @classmethod
    def build(self, stagerun_micro_program:StageRunMicroProgram) -> dict[str, ControlFlowGraph]:
        """
        Builds CFGs only from the bodies of prefilters in a StageRunProgram.
        Each PreFilter → one ControlFlowGraph.
        """
        graphs: dict[str, ControlFlowGraph] = {}
        global_node_id = 0      # ensures unique IDs across all graphs

        for pf in stagerun_micro_program.prefilters:
            cfg = ControlFlowGraph(name=pf.name)

            last_node_id = None

            # Only process the BODY of each PreFilter
            for micro in pf.body:
                node = CFGNode(
                    id=global_node_id,
                    micro_instr=micro,
                    deps=[last_node_id] if last_node_id is not None else []
                )
                cfg.add_node(node)

                # increment IDs for global uniqueness
                last_node_id = global_node_id
                global_node_id += 1

            # Register the CFG for this prefilter
            graphs[pf.name] = cfg

        return graphs


logger = logging.getLogger(__name__)

# Planner implementation to place nodes into stage/table and assign cf_id
class Planner:
    def __init__(self):
        pass

    @staticmethod
    def _extract_stage_number(stage_name: str) -> int:
        m = re.match(r"^s(\d+)$", stage_name)
        return int(m.group(1)) if m else None

    @staticmethod
    def _stage_table_list(stage_dict: Dict) -> List[str]:
        """
        Return list of table keys in the order they appear in the stage dict.
        """
        return list(stage_dict.keys())

    @staticmethod
    def _instr_in_table(stage_dict: Dict, table_name: str, instr_name: str) -> bool:
        instr_list = stage_dict.get(table_name, [])
        if not instr_list:
            return False
        return instr_name in instr_list

    @classmethod
    def plan(self,
             micro_program: StageRunMicroProgram,
             cfg_graphs: Dict[str, ControlFlowGraph],
             pipeline: Dict = None):
        """
        Improved planner that preserves intra-stage table-order constraints:
          - Next node must be in same stage but a strictly *later* table index,
            or in a later stage (from its first table onward).

        Parameters:
          - micro_program: (optional) StageRunMicroProgram
          - cfg_graphs: dict[name -> ControlFlowGraph]
          - pipeline: engine ISA pipeline dict, e.g. {"s1": {...}, "s2": {...}}

        Returns:
          - {"graphs": cfg_graphs, "failed": failed_nodes}
        """
        # If pipeline not given, try to get it from state manager
        if pipeline is None:
            try:
                # import lib.controller.state_manager as sm
                engine_isa = sm.get_engine_ISA(sm.get_running_engine_key())
                pipeline = engine_isa.get("pipeline", {})
            except Exception as e:
                logger.warning("Pipeline not provided and could not be loaded: %s", e)
                pipeline = {}

        # failed_nodes = []  # tuples (graph_name, node_id, instr_name)

        # Pre-sort stages in ascending order
        # stages_sorted = sorted(pipeline.keys(), key=self._extract_stage_number)

        # Stages alredy come in ascending order
        stages_sorted = pipeline.keys()

        # Helper: find a stage index in stages_sorted by numeric stage number
        # def find_stage_index_by_number(stage_number: int) -> Optional[int]:
        #     for i, s in enumerate(stages_sorted):
        #         if self._extract_stage_number(s) == stage_number:
        #             return i
        #     return None

        cf_counter = 1

        # Deterministic ordering of graphs
        # for graph_name in sorted(cfg_graphs.keys()):
            # cfg = cfg_graphs[graph_name]
        for cfg in cfg_graphs.values():

            # assign cf_id
            cf_id = cf_counter
            cfg.initial_cf_id_f1 = cf_counter
            cfg.initial_cf_id_f2 = 0
            cf_counter += 1

            # annotate nodes' cf_id
            for node in cfg.nodes:
                node.cf_id = cf_id
                node.allocated_flow = 1
                

            # track the "current" position we are allowed to place the next node
            # represented by (stage_index_in_stages_sorted, table_index_in_stage)
            # initialize as None meaning we will search from stage 0, table 0 for first node
            prev_stage_idx = None
            prev_table_idx = None

            # iterate nodes in order
            for node in cfg.nodes:
                instr_name = node.micro_instr.instr_name
                placed = False

                # Determine starting stage index and table index for search
                if prev_stage_idx is None:
                    # first node -> start from beginning of stages and tables
                    start_stage_idx = 0
                    start_table_idx = 0
                else:
                    # try same stage but strictly later table index first
                    start_stage_idx = prev_stage_idx
                    start_table_idx = prev_table_idx + 1  # strictly later table

                # Search stages from start_stage_idx .. end
                for s_idx in range(start_stage_idx, len(stages_sorted)):
                    stage_name = f"s{s_idx}"
                    stage_dict = pipeline.get(stage_name, {})

                    # get tables in stage in order
                    tables = self._stage_table_list(stage_dict)

                    # If we're on the start_stage_idx, start at start_table_idx; else start at 0
                    t_start = start_table_idx if s_idx == start_stage_idx else 0

                    # iterate tables in this stage from t_start
                    for t_idx in range(t_start, len(tables)):
                        tname = tables[t_idx]
                        if self._instr_in_table(stage_dict, tname, instr_name):
                            # place node here
                            node.allocated_stage = self._extract_stage_number(stage_name)
                            node.allocated_table = tname
                            # record for next node placement
                            prev_stage_idx = s_idx
                            prev_table_idx = t_idx
                            placed = True
                            break
                    if placed:
                        break

                if not placed:
                    raise NotImplementedError("Exceeds All Stages of the pipeline; need to recirculate")
                    # # Not found anywhere -> record failure and reset prev markers so subsequent nodes
                    # # still try from beginning (or you might prefer to keep prev position - here we reset)
                    # failed_nodes.append((cfg.name, node.id, instr_name))
                    # node.allocated_stage = None
                    # node.allocated_table = None
                    # # to keep behavior strict for following nodes, reset prev pointers so they start from stage 0
                    # prev_stage_idx = None
                    # prev_table_idx = None

        return cfg_graphs


class Installer:
    def __init__(self):
        pass

    @staticmethod
    def install_node(node: CFGNode):
        # Current Instruction Key
        node.micro_instr.kwargs['ni'] = node.cf_id

        # Next Instruction Key
        if node.allocated_table != P1_TABLE:
            node.micro_instr.kwargs['instr_id'] = node.cf_id

        table = node.allocated_table
        table_to_install_rule = None
        if table in P1_TABLE:
            table_to_install_rule = sm.engine_controller.p1_table
        elif table in P2_TABLE:
            table_to_install_rule = sm.engine_controller.p2_table
        elif table in SPEC_TABLE:
            table_to_install_rule = sm.engine_controller.spec_table

        # I want to run
        if table_to_install_rule:
            if node.allocated_stage - 1 == 0:
                allocation_stage = 1
            else:
                allocation_stage = node.allocated_stage - 1  
            table_to_install_rule._set_location_(f"SwitchIngress.f{node.allocated_flow}_i{allocation_stage}")
            
            # call method by name
            func = getattr(table_to_install_rule, node.micro_instr.instr_name, None)
            if func is None:
                raise RuntimeError(f"Instrução {node.micro_instr.instr_name} não existe no objeto {table_to_install_rule}")
            
            # Execute with the arguments
            func(**node.micro_instr.kwargs)

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


        print("keys=",keys)

        print("instr=",instr)
        print("kwargs=",kwargs)


        # Choose table
        table_to_install_rule = sm.engine_controller.pre_filter_mechanism

        func = getattr(table_to_install_rule, instr, None)
        if func is None:
            raise RuntimeError(f"Instruction {instr} does not exist in PreFilter Mechanism (key installation).")

        func(**kwargs)

    @staticmethod
    def install_default_action(prefilter: PreFilter):
        """
        Installs the default action for the prefilter (drop, fwd, fwd_and_enqueue).
        """
        default = prefilter.default_action
        if (default):
            instr = default.instr_name
            kwargs = default.kwargs

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

            # 1. Keys
            self.install_prefilter_key(prefilter, cf_id, cf_id_2, pkt_id)

            # 2. Default Action
            self.install_default_action(prefilter)

            # 3. Body
            for node in cfg.nodes:
                self.install_node(node)

            pkt_id += 1
