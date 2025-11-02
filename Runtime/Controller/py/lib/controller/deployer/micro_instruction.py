"""
MicroInstruction Lowering
-------------------------

Converts StageRunGraph (compiler output) into a MicroGraph, expanding each
high-level instruction into one or more micro-operations (MicroInstructions).

All logic is encapsulated in the MicroInstructionParser class.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from .types import MicroGraph, MicroNode, MicroEdge, MicroInstruction, MicroInstructionError, MicroEffect
from lib.utils.manifest_parser import get_pnum_from_endpoints
import lib.controller.state_manager as sm
from lib.tofino.constants import *
from Core.stagerun_isa import ISA
import re 
import ipaddress

tofino_headers = {
    'IPV4.TTL': HEADER_IPV4_TTL,
    'IPV4.DST': HEADER_IPV4_DST,
    'IPV4.SRC': HEADER_IPV4_SRC,
    # 'IPV4.PROTO': HEADER_IPV4_PROTO,
    'TCP.ACK_NO': HEADER_TCP_ACK_NO,
    'TCP.SEQ_NO': HEADER_TCP_SEQ_NO,
    'TCP.FLAGS': HEADER_TCP_FLAGS,
    'IPV4.ID': HEADER_IPV4_IDENTIFICATION,
}
headers_to_fetch = {
    'IPV4.TTL': "fetch_ipv4_ttl",
    'IPV4.DST': "fetch_ipv4_dst",
    'IPV4.SRC': "fetch_ipv4_src",
    'IPV4.LEN': "fetch_ipv4_total_len",
    'IPV4.PROTO': "fetch_ipv4_protocol",
    'TCP.ACK_NO': "fetch_tcp_ack_no",
    'TCP.SEQ_NO': "fetch_tcp_seq_no",
    'TCP.FLAGS': "fetch_tcp_flags",
    'IPV4.ID': "fetch_ipv4_identification",
}

_OP_MAP = {"==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE"}

# ============================================================
# Id allocator helper
# ============================================================

class IdAlloc:
    def __init__(self, start: int = 1):
        self._n = start

    def next(self) -> int:
        i = self._n
        self._n += 1
        return i


# ============================================================
# Parser class
# ============================================================


class MicroInstructionParser:
    """
    Converts StageRunGraph → MicroGraph.
    """

    def __init__(self, isa: Dict[str, Any], manifest: Dict[str, Any], id_alloc: Optional[IdAlloc] = None):
        self.isa = isa
        self.manifest = manifest
        self.id_alloc = id_alloc or IdAlloc()
        self.graphs: List[MicroGraph] = []

    # ------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------

    def to_micro(self, stage_run_graphs: List[Dict[str, Any]]) -> List[MicroGraph]:
        """
        Converts StageRunGraph → MicroGraph.
        Each StageRun instruction expands into one or more MicroNodes, each with a MicroEffect.
        """
        out_graphs: List[MicroGraph] = []

        for graph in stage_run_graphs:
            mg = MicroGraph(graph_id=graph["graph_id"])
            mg.keys = self._translate_keys_to_micro(graph.get("keys", []))
            mg.default_action = self._translate_default_action_to_micro(graph.get("default_action"))
            expand_map: Dict[int, List[int]] = {}
            node_id = 0
            for srun_node in graph.get("nodes", []):
                srun_id = srun_node["id"]
                op = srun_node["op"]
                args = srun_node.get("args", {})
                compiler_effect = srun_node.get("effect", None)

                instrs, effects = self._translate_instr_to_micro(op, args, compiler_effect)
                
                if len(instrs) != len(effects):
                    raise MicroInstructionError(f"Mismatch: {op} returned {len(instrs)} instrs and {len(effects)} effects")

                for mi, eff in zip(instrs, effects):
                    node_id += 1
                    # merge compiler effect (if present)
                    # if compiler_effect:
                    #     comp_eff = MicroEffect(
                    #         reads=set(compiler_effect.get("reads", [])),
                    #         writes=set(compiler_effect.get("writes", [])),
                    #         uses=set(compiler_effect.get("uses", [])),
                    #     )
                    #     eff = eff.merge(comp_eff)

                    node = MicroNode(
                        id=node_id,
                        instr=mi,
                        graph_id=graph["graph_id"],
                        parent_node_id=srun_id,
                        effect=eff,
                    )
                    mg.nodes[node.id] = node
                    expand_map.setdefault(srun_id, []).append(node.id)

            # ligações (mesma lógica)
            for e in graph.get("edges", []):
                srcs = expand_map.get(e["src"], [])
                dsts = expand_map.get(e["dst"], [])
                for src_id in srcs:
                    for dst_id in dsts:
                        mg.edges.append(MicroEdge(src=src_id, dst=dst_id, dep=e.get("dep", "DATA")))

            out_graphs.append(mg)

        return out_graphs


    # ------------------------------------------------------------
    # Node lowering
    # ------------------------------------------------------------
    # def _emit_if(self, args: Dict[str, Any], graph_id: str, parent_id: int, mg: MicroGraph, manifest: Dict[str, Any]) -> int:
    #     """
    #     Emite um IF (pode ser nested). Retorna o node_id do decide criado.
    #     """
    #     # cria nó decide
    #     nid_if = self._emit_instrs([MicroInstruction("decide", {"cond": "expr"})], graph_id, parent_id, mg)[0]

    #     # TRUE + ELIFs
    #     for idx, br in enumerate(args.get("branches", [])):
    #         label = "true" if idx == 0 else f"elif-{idx}"
    #         first_body_id = None
    #         for instr in br.get("body", []):
    #             # ⚠️ se este instr for outro IF, chamamos recursivamente o _emit_if
    #             if instr["op"].upper() == "IF":
    #                 inner_decide = self._emit_if(instr["args"], graph_id, parent_id, mg, manifest)
    #                 if first_body_id is None:
    #                     first_body_id = inner_decide
    #             else:
    #                 lst = self._translate_instr_to_micro(instr["op"], instr.get("args", {}), manifest)
    #                 first_ids = self._emit_list(lst, graph_id, parent_id, mg)
    #                 if first_ids and first_body_id is None:
    #                     first_body_id = first_ids[0]
    #         if first_body_id:
    #             mg.edges.append(MicroEdge(src=nid_if, dst=first_body_id, dep="CONTROL", label=label))

    #     # ELSE
    #     else_body = args.get("else_body") or []
    #     if else_body:
    #         first_body_id = None
    #         for instr in else_body:
    #             if instr["op"].upper() == "IF":
    #                 inner_decide = self._emit_if(instr["args"], graph_id, parent_id, mg, manifest)
    #                 if first_body_id is None:
    #                     first_body_id = inner_decide
    #             else:
    #                 lst = self._translate_instr_to_micro(instr["op"], instr.get("args", {}), manifest)
    #                 first_ids = self._emit_list(lst, graph_id, parent_id, mg)
    #                 if first_ids and first_body_id is None:
    #                     first_body_id = first_ids[0]
    #         if first_body_id:
    #             mg.edges.append(MicroEdge(src=nid_if, dst=first_body_id, dep="CONTROL", label="else"))

    #     return nid_if

    # def _emit_instrs(self, micro_instrs: List[MicroInstruction],
    #                  graph_id: str, parent_id: int, mg: MicroGraph) -> List[int]:
    #     ids: List[int] = []
    #     for mi in micro_instrs:
    #         nid = self.id_alloc.next()
    #         node = MicroNode(id=nid, instr=mi, graph_id=graph_id, parent_node_id=parent_id)
    #         mg.nodes[nid] = node
    #         if ids:
    #             mg.edges.append(MicroEdge(src=ids[-1], dst=nid, dep="DATA"))
    #         ids.append(nid)
    #     return ids


    def _translate_keys_to_micro(self, keys) -> Dict:

        def cidr_to_ip_and_mask(ip_cidr: str):
            """Converts CIDR (e.g. '10.10.1.0/24') to (ip_int, mask_int)."""
            network = ipaddress.IPv4Network(ip_cidr, strict=False)
            ip_int = int(network.network_address)
            mask_int = int(network.netmask)
            return ip_int, mask_int
        
            # Defaults para todos os campos aceites pelo set_pkt_id()
        args = {
            # # Table Keys
            # "ig_port": [0, 0],
            # "original_ig_port": [0, 0],
            # "total_pkt_len": [0, 0],
            # "tcp_dst_port": [0, 0],
            # "ipv4_src_addr": [0, 0],
            # "ipv4_dst_addr": [0, 0],
            # "tcp_flags": [0, 0],
            # "ipv4_proto": [0, 0],
            # "udp_sport": [0, 0],
            # "udp_dport": [0, 0],

            # # Action Parameters
            # "pkt_id": 0,
            # "ni_f1": INSTRUCTION_FINISH,
            # "ni_f2": INSTRUCTION_FINISH,
            # # "program_id": pid
        }

        # Preenche com base nas keys do prefilter
        for key in keys:
            field = key["field"]
            operand_raw = key["operand"]
            operand_val = getattr(operand_raw, "value", operand_raw)
            operand = self._mode_from_op(str(operand_val))
            value = key["value"]

            if operand == "EQ":
                if field == "PKT.PORT":
                    port = get_pnum_from_endpoints(self.manifest, value)
                    dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(port, 0)
                    args["ig_port"] = [dev_port, MASK_PORT]

                elif field == "IPV4.DST":
                    ip_cidr = value  # e.g. "10.10.1.0/24"
                    ip_int, mask_int = cidr_to_ip_and_mask(ip_cidr)
                    args["ipv4_dst_addr"] = [ip_int, mask_int]

                elif field == "IPV4.PROTO":
                    args["ipv4_proto"] = [value, MASK_IPV4_PROTO]

            elif operand in ("NE", "LT", "LE", "GT", "GE"):
                raise MicroInstructionError(f"Operand '{operand_val}' for field '{field}' is not supported yet")
            # TODO: implement other fields for the KEY

        return {"instr": "set_pkt_id", "kwargs": args}


    def _translate_default_action_to_micro(self, default_action:Dict):
        if default_action and 'op' in default_action and 'args' in default_action:
            instr_name = default_action['op']
            args = default_action['args']

            instr = {}
            kwargs = {}

            if instr_name == ISA.DROP.value:
                # Drop action
                instr = "drop"
                kwargs = {
                        "pkt_id": 0,
                        # "port": 0,  # or None if not used by drop()
                        # "program_id": pid
                    }
                return {"instr": instr, "kwargs": kwargs}

            elif instr_name == ISA.FWD.value:
                # Forward to a specific port
                dest = args["dest"]
                front_port = get_pnum_from_endpoints(self.manifest, dest)
                dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)

                instr = "fwd"
                kwargs = {
                        "pkt_id": 0,
                        "port": dev_port,
                    }
                return {"instr": instr, "kwargs": kwargs}
            
            elif instr_name == ISA.FWD_AND_ENQUEUE.value:
                # Forward and enqueue to queue
                dest = args["dest"]
                qid = args["qid"]
                front_port = get_pnum_from_endpoints(self.manifest, dest)
                dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)

                instr = "fwd_and_enqueue"
                kwargs = {
                        "pkt_id": 0,
                        "port": dev_port,
                        "qid": qid
                    }
                return {"instr": instr, "kwargs": kwargs}

            else:
                raise MicroInstructionError(f"Error Parsing MicroInstruction DefaultAction {default_action}")
        
        return None

    def _translate_instr_to_micro(self, op: str, args: Dict[str, Any], compiler_effects) -> Tuple[List[MicroInstruction], List[MicroEffect]]:
        """
        Translates one StageRun instruction into micro instructions and effects.
        Returns a tuple (micro_instrs, micro_effects).
        """
        instrs: List[MicroInstruction] = []
        effects: List[MicroEffect] = []

        # --- FWD ---
        if op == ISA.FWD.value:
            front_port = get_pnum_from_endpoints(self.manifest, args["dest"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)
            instrs = [MicroInstruction(name="fwd_ni", kwargs={"port": dev_port})]
            effects = [MicroEffect()]  # no read/write impact

        # --- FWD_AND_ENQUEUE ---
        elif op == ISA.FWD_AND_ENQUEUE.value:
            front_port = get_pnum_from_endpoints(self.manifest, args["dest"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)
            instrs = [MicroInstruction(name="fwd_ni", kwargs={"port": dev_port, "qid": args["qid"]})]
            effects = [MicroEffect()]

        # --- DROP ---
        elif op == ISA.DROP.value:
            instrs = [MicroInstruction(name="fwd_ni", kwargs={"mark_to_drop": 1})]
            effects = [MicroEffect()]

        # --- HINC ---
        elif op == ISA.HINC.value:
            header = args['target']
            normal_header = self._hdr_fetch_micro(header, False)
            spec_header = self._hdr_fetch_micro(header, True)

            instrs = [
                MicroInstruction(name=normal_header, kwargs={}, alternative=spec_header),
                MicroInstruction(name="sum_ni", kwargs={"header_update": 1, "header_id": tofino_headers[header], "const_val": args["value"]}),
            ]
            effects = [MicroEffect(reads={header}), MicroEffect(writes={header})]

        # --- HTOVAR ---
        elif op == ISA.HTOVAR.value:
            header = args['target']
            var_name = args.get("var_name", "")
            normal_header = self._hdr_fetch_micro(header, False)
            spec_header = self._hdr_fetch_micro(header, True)
            instrs = [
                MicroInstruction(
                    name=normal_header,
                    kwargs={"var_update": 1, "var_name": var_name},
                    alternative=spec_header,
                )
            ]
            effects = [MicroEffect(reads={header}, writes={var_name})]

        # --- PATTERN ---
        elif op == ISA.PADTTERN.value:
            instrs = [MicroInstruction(name="initialize_pad_ni", kwargs={"mode": MODE_PADTTERN})]
            effects = [MicroEffect()]

        # --- CLONE ---
        elif op == ISA.CLONE.value:
            front_port = get_pnum_from_endpoints(self.manifest, args["port"])
            dev_port = sm.engine_controller.port_mechanism.port_hdl.get_dev_port(front_port, 0)
            instrs = [MicroInstruction(name="initialize_activate_ni", kwargs={})]
            effects = [MicroEffect()]

        # --- IF ---
        elif op == ISA.IF.value:
            branches = args.get("branches", [])
            cond_ir = {}
            # cond_ir = self._cond_to_ir(branches)
            # reads = self._cond_collect_reads_from_dnf([cl for br in cond_ir["branches"] for cl in br["dnf"]])
            """
            {
                "condition": {
                  "left": "size",
                  "op": "EQ",
                  "right": 1500
                },
                "body": [
                  {
                    "op": "FWD",
                    "args": {
                      "port": "PC2_OUT"
                    }
                  }
                ]
              },
              {
                "condition": {
                  "left": "size",
                  "op": "EQ",
                  "right": 1600
                },
                "body": [
                  {
                    "op": "FWD",
                    "args": {
                      "port": "PC1_OUT"
                    }
                  }
                ]
              }
            """
            print(compiler_effects)
            _reads = compiler_effects.get("reads", [])
            _writes = compiler_effects.get("writes", [])

            reads = [item.removeprefix("var.").removeprefix("hdr.") for item in _reads]
            writes = [item.removeprefix("var.").removeprefix("hdr.") for item in _writes]

            # for br in branches:
            #     br["condition"] 
                
            #     for i in br["body"]:
            #         lst_micros, lst_effects = self._translate_instr_to_micro(i["op"], i["args"])


            instrs = [MicroInstruction(name="decide", kwargs={"cond_ir": cond_ir, "reads": reads})]
            effects = [MicroEffect(reads=set(reads), writes=set(writes))]

        else:
            raise MicroInstructionError(f"Unknown instruction '{op}' cannot be translated.")

        return instrs, effects

    # ------------------------------------------------------------
    # Header micro helpers
    # ------------------------------------------------------------

    def _mode_from_op(self, op: str) -> str:
        op = op.upper()
        return op if op in _OP_MAP.values() else _OP_MAP.get(op, "EQ")

    def _cond_collect_reads_from_dnf(self, dnf):
        reads = set()
        for clause in dnf:
            for term in clause:
                v = term.get("var")
                if isinstance(v, str):
                    reads.add(v)
        return sorted(reads)

    def _cond_to_dnf_from_struct(self, node) -> list[list[dict]]:
        """
        Converte uma árvore:
        {"left": <expr>, "op": "&&"|"||", "right": <expr>}
        ou um comparador:
        {"left": "proto", "op": "==", "right": "200"}
        em DNF: lista de cláusulas AND; OR combina cláusulas.
        """
        if not isinstance(node, dict):
            # ex: else branch (sem condição)
            return [[]]  # 'true' (cláusula vazia)

        op = node.get("op")
        # folha comparador var OP const
        if op in ("==","!=","<","<=",">",">="):
            var = node.get("left")
            const = node.get("right")
            # normaliza números
            try:
                const = int(const)
            except Exception:
                pass
            return [[{"var": str(var), "op": self._mode_from_op(op), "const": const}]]

        # nós booleanos
        if op in ("&&", "AND"):
            left_dnf  = self._cond_to_dnf_from_struct(node.get("left"))
            right_dnf = self._cond_to_dnf_from_struct(node.get("right"))
            # AND: produto cartesiano das cláusulas
            out = []
            for L in left_dnf:
                for R in right_dnf:
                    out.append([*L, *R])
            return out

        if op in ("||", "OR"):
            left_dnf  = self._cond_to_dnf_from_struct(node.get("left"))
            right_dnf = self._cond_to_dnf_from_struct(node.get("right"))
            # OR: concatena listas de cláusulas
            return [*left_dnf, *right_dnf]

        # fallback: se não reconhecemos, trata como 'true'
        return [[]]

    def _cond_to_ir(self, branches: list[dict]) -> dict:
        """
        Aceita branches do exporter:
        { "label": "...", "condition": {... ou "text": "..."} , "body": [...] }
        Devolve:
        {"branches": [ {"label": "...", "dnf": [[term,...], ...]}, ... ]}
        """
        out = {"branches": []}
        for idx, br in enumerate(branches):
            label = br.get("label") or ("true" if idx == 0 else f"elif-{idx}")
            cond = br.get("condition")

            # 1) condição estruturada {"left":...,"op":...,"right":...}
            if isinstance(cond, dict) and ("left" in cond or "op" in cond or "right" in cond):
                dnf = self._cond_to_dnf_from_struct(cond)

            # 2) condição textual {"text": "..."} (mantém fallback antigo se ainda existir)
            elif isinstance(cond, dict) and "text" in cond:
                dnf = self._parse_cond_text_to_dnf(cond["text"])

            # 3) string simples
            elif isinstance(cond, str):
                dnf = self._parse_cond_text_to_dnf(cond)

            # 4) sem condição (ELSE)
            else:
                dnf = [[]]  # 'true'

            out["branches"].append({"label": label, "dnf": dnf})
        return out



    def _hdr_extract_micro(self, hdr: str) -> str:
        h = (hdr or "").upper()
        if h == "IPV4.PROTO":
            return "hdr_extract_ipv4_proto"
        if h == "IPV4.LEN":
            return "hdr_extract_ipv4_len"
        return "hdr_extract_generic"

    def _hdr_fetch_micro(self, hdr: str, speculative: bool = False) -> str:
        h = (hdr or "").upper()

        return f"speculative_{headers_to_fetch[h]}" if speculative else headers_to_fetch[h]
