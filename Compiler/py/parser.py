# src/stagerun_compiler/parser.py
from pathlib import Path
from lark import Lark, Transformer
from lark.visitors import v_args
import sys

# Importa as dataclasses (agora sem o ast_utils.Ast inheritance)
from ast_nodes import * # Mantenha a importação, mas remova o '_Ast' e o ast_utils do ast_nodes.py

GRAMMAR_PATH = "py/grammar/stagerun_grammar.lark"


# Usamos v_args(inline=True) para que o Lark nos envie os argumentos por posição.
@v_args(inline=True)
class StageRunTransformer(Transformer):
    """
    Constrói a AST StageRun (dataclasses) a partir do Lark Tree,
    sem depender do ast_utils.create_transformer.
    """
    
    # --- Métodos de Limpeza/Tokens ---
    
    def value(self, item): 
        # item é o Token ('NAME' ou 'STRING').
        val = item.value
        if item.type == 'STRING':
            return val[1:-1] # Remove as aspas
        return val

    def SIGNED_NUMBER(self, item):
        return int(item.value)
    
    def key_name(self, name1, name2):
        # name1 e name2 são Tokens, o '.' é ignorado
        return f"{name1.value}.{name2.value}"

    def header_operand(self, name1, name2):
        return f"{name1.value}.{name2.value}"

    # --- Métodos de Construção da AST (Correspondência de Regra) ---
    
    def start(self, *statements):
        # A regra 'start' (statement+) retorna a lista final de nós AST
        return list(statements)

    def port_declr(self, name): # Mantenha o nome da regra (port_declr)
        return PortDecl(name=name.value) 

    # Regras de Instrução
    def fwd_instr(self, dest):
        return ForwardInstr(dest=dest.value)

    def drop_instr(self): # Não recebe argumentos além de self
        return DropInstr()
        
    def hinc_instr(self, target, value):
        # Target e Value já foram limpos pelos métodos key_name/SIGNED_NUMBER
        return HeaderIncrementInstruction(target=target, value=value)

    # Regras de Cláusula
    def key_clause(self, key_name, value): # A regra Lark tem 'KEY' key_name '==' value
        # O "KEY" e o "==" são ignorados.
        return KeyClause(field=key_name, value=value)

    def default_instr(self, action): # Regra que apenas encaminha para FWD/DROP
        return action # Retorna o nó FwdInstr ou DropInstr

    def default_clause(self, action): # A regra Lark é 'DEFAULT' default_instr
        return DefaultClause(action=action)

    # Correção do problema de iterabilidade e agrupamento
    def body_clause(self, *statements):
        # A tupla *statements contém 0 ou mais nós de instrução. list() é sempre uma lista.
        return BodyClause(statements=list(statements)) 

    # Regra de Agrupamento Intermédio
    def prefilter_body(self, *items):
        # Agrupa a lista de cláusulas em chaves, default, body
        keys = [item for item in items if isinstance(item, KeyClause)]
        default = next((item for item in items if isinstance(item, DefaultClause)), None)
        body = next((item for item in items if isinstance(item, BodyClause)), None)
        
        # Devolve um dicionário temporário que a regra 'prefilter' irá consumir.
        return {'keys': keys, 'default': default, 'body': body}

    # Regra Final
    def prefilter(self, name, body_data):
        # name é o Token (NAME)
        return PreFilter(
            name=name.value,
            keys=body_data['keys'],
            default=body_data['default'],
            body=body_data['body']
        )


# ------------------------------
# Parser
# ------------------------------

parser = Lark.open(str(GRAMMAR_PATH), parser="lalr", propagate_positions=True)

def parse_program(text: str):
    tree = parser.parse(text)
    # Apenas o seu transformer é usado.
    return StageRunTransformer().transform(tree)