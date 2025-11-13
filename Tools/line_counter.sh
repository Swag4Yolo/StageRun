#!/bin/bash

# 1. Encontra o diretório absoluto onde o script está guardado
# Esta técnica robusta lida com symlinks e diferentes formas de execução.
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# 2. Guarda o diretório atual de trabalho na stack e muda para o SCRIPT_DIR
# O '|| exit' é importante caso a mudança de diretório falhe (e.g., permissões)
pushd "$SCRIPT_DIR" > /dev/null || exit

# --- Bloco de Comandos ---

# 3. Executa o comando de contagem a partir do diretório do script
# find . -iname '*.py' -not -path '*_env*' | xargs wc -l  # (versão xargs)
find .. -iname '*.py' -not -path '*_env*' -not -path '*backup*' -exec wc -l {} +

# --- Fim do Bloco de Comandos ---

# 4. Restaura o diretório de trabalho original da stack, 
#    levando-o de volta para onde começou.
popd > /dev/null

# find . -iname '*.py' -not -path '*_env*' | xargs wc -l
# tree -I '.vscode/|*.git*|*_env*'