# Compiler/py/stagerun_graph/graph_builder.py
from .graph_core import StageRunGraph, StageRunNode
from .effect_registry import effect_of_instr
from Core.ast_nodes import *
from Core.stagerun_isa import ISA

class StageRunGraphBuilder:
    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self._next_id = 1
        self.nodes = {}
        self.edges = []
        self.last_writer = {}        # mapa de última escrita por variável
        self.resource_tail = {}      # última instrução que usou recurso

        # Necessary for PreFilter 
        self.keys = []
        self.default_action = {}

    def _new_node(self, instr, effect):
        nid = self._next_id
        self._next_id += 1
        node = StageRunNode(id=nid, instr=instr, effect=effect)
        self.nodes[nid] = node
        return node

    def _add_edge(self, src, dst, dep):
        self.edges.append((src, dst, dep))

    def _finalize(self) -> StageRunGraph:
        g = StageRunGraph(graph_id=self.graph_id)
        
        # 1. Add Keys
        g.keys = self.keys
        # 2. Add default_action
        g.default_action = self.default_action
        # 3. Add Instructions
        for node in self.nodes.values():
            g.add_node(node)
        for (src, dst, dep) in self.edges:
            g.add_edge(src, dst, dep)

        return g

    def _build_instructions(self, instructions: list):
        # prev_nodes = []
        for instr in instructions:
            eff = effect_of_instr(instr)
            node = self._new_node(instr, eff)

            # 1. ligar sequencialmente (fallthrough)
            # for p in prev_nodes:
            #     self._add_edge(p, node.id, "FALLTHROUGH")

            # 2. dependências de dados
            for read in eff.reads:
                if read in self.last_writer:
                    self._add_edge(self.last_writer[read], node.id, "DATA")

            # 3. dependências de recursos (port, queue, pattern, etc.)
            for res in eff.uses:
                if res in self.resource_tail:
                    self._add_edge(self.resource_tail[res], node.id, "RESOURCE")
                self.resource_tail[res] = node.id

            # atualizar escritores
            for w in eff.writes:
                self.last_writer[w] = node.id

            # prev_nodes = [node.id]

        # return self._finalize()
    
    def _build_keys(self, keys:List[HandlerKey]):
        for key in keys:
            self.keys.append({
                "field": key.field, 
                "operand": key.operand, 
                "value": key.value
                })


    def _build_default_action(self, instr: InstructionNode):
        if instr:
            if isinstance(instr, FwdInstr):
                self.default_action = {
                    "op": ISA.FWD.value, 
                    "args": {
                        "port": instr.port
                        }
                    }
            elif isinstance(instr, FwdAndEnqueueInstr):
                self.default_action = {
                    "op": ISA.FWD_AND_ENQUEUE.value, 
                    "args": {
                        "port": instr.port, "qid" : instr.qid
                        }
                    }
            elif isinstance(instr, DropInstr):
                self.default_action = {"op": ISA.DROP.value}

    def build(self, keys, default_action, instructions):
        self._build_keys(keys)
        self._build_default_action(default_action)
        self._build_instructions(instructions)
        return self._finalize()
