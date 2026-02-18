#!/bin/bash

# Número de iterações por programa
N_RUNS=10
LOG_FILE="apps_deploy.log"

# Timeout máximo (em segundos) para o bfshell aparecer
TIMEOUT=60

# Lista de programas P4
P4_PROGRAMS=(
        
    # ======= Programas =======
    #        SDE 9.13.2
    # "Cerberus/multi3/example3.p4"
    # "Mew-prototype/core/crossfire/mew-core-crossfire.p4"
    # "BRI/o2/evaluation/programs/NativeP4Apps/NetHide/NetHide.p4"
    # "p4control/switch/p4control.p4"
    # "BRI/o2/evaluation/programs/NativeP4Apps/PortKnocker/PortKnocker.p4"
    # "BRI/o2/evaluation/programs/NativeP4Apps/StatefulFirewall/StatefulFirewall.p4"
    # "p4-projects/SmartCookie/p4src/benchmark/SmartCookie-CRC_sde_9.13.3.p4"
    # "NetShuffle/tofino-v2/netshuffle.p4"


    # ======= Programas =======
    #        SDE 9.7.0
    # "NetWarden/release/pack_mal/pack_mal.p4"
    # "activermt/activermt/dataplane/active.p4"
    "DANE/NativeP4Apps/Ditto/Tofino1/originalImplementation/p4/traffic_pattern_tofino/p4src/traffic_pattern_tofino.p4"

    # ======= Frameworks =======
    #        SDE 9.13.2
    # "P4runpro/custom/p4src/p4runpro.p4"



    # ======= Frameworks =======
    #        SDE 9.7.0
)

# Limpa log anterior
> "$LOG_FILE"

echo "=== Início das execuções ($(date)) ===" | tee -a "$LOG_FILE"
echo "Iterações: $N_RUNS | Timeout: ${TIMEOUT}s" | tee -a "$LOG_FILE"
echo "Usando SDE: $SDE" | tee -a "$LOG_FILE"

# Verifica se tmux está instalado
if ! command -v tmux &>/dev/null; then
    echo "❌ ERRO: tmux não está instalado. Instala-o com 'sudo apt install tmux'." | tee -a "$LOG_FILE"
    exit 1
fi

# Loop pelos programas
for program_path in "${P4_PROGRAMS[@]}"; do
    program_name=$(basename "$program_path" .p4)

    echo -e "\n=============================================" | tee -a "$LOG_FILE"
    echo "🏷️  Programa: $program_name" | tee -a "$LOG_FILE"
    echo "Caminho: $program_path" | tee -a "$LOG_FILE"

    if [[ ! -f "$program_path" ]]; then
        echo "⚠️  ERRO: Ficheiro não encontrado: $program_path" | tee -a "$LOG_FILE"
        continue
    fi

    for ((i=1; i<=N_RUNS; i++)); do
        echo -e "\n🔁 Execução $i de $N_RUNS - $(date)" | tee -a "$LOG_FILE"

        # Limpa processos e sessões antigas
        pkill -9 bf_switchd 2>/dev/null
        pkill -9 run_switchd.sh 2>/dev/null
        tmux kill-session -t "switchd_${program_name}" 2>/dev/null
        sleep 2

        # Espera a porta 50052 ficar livre
        PORT=50052
        while lsof -i:$PORT >/dev/null 2>&1; do
            echo "⚠️  Porta $PORT ainda ocupada — a aguardar..." | tee -a "$LOG_FILE"
            sleep 2
        done

        tmp_output="tmp_${program_name}_run${i}.log"
        rm -f "$tmp_output"
        touch "$tmp_output"

        start_time=$(date +%s.%N)
        echo "🟡 A iniciar switchd (via tmux)..." | tee -a "$LOG_FILE"

        # Cria uma nova sessão tmux detached
        tmux new -d -s "switchd_${program_name}"

        # Direciona o output da sessão tmux para o ficheiro de log
        tmux pipe-pane -t "switchd_${program_name}" "cat >> $tmp_output"

        # Envia o comando para dentro da sessão
        tmux send-keys -t "switchd_${program_name}" "cd; sudo $SDE/run_switchd.sh -p $program_name" C-m

        found=0
        elapsed_time=0
        start_sec=$(date +%s)

        # Espera até "bfshell>" aparecer ou timeout
        while true; do
            if grep -q "bfshell>" "$tmp_output"; then
                end_time=$(date +%s.%N)
                elapsed=$(echo "$end_time - $start_time" | bc)
                echo "✅ bfshell iniciado após ${elapsed}s" | tee -a "$LOG_FILE"
                found=1
                break
            fi

            now=$(date +%s)
            elapsed_time=$(( now - start_sec ))
            if [[ $elapsed_time -ge $TIMEOUT ]]; then
                echo "⏰ TIMEOUT após ${TIMEOUT}s — bfshell não iniciou" | tee -a "$LOG_FILE"
                break
            fi
            sleep 0.2
        done

        # Termina a sessão tmux
        tmux kill-session -t "switchd_${program_name}" 2>/dev/null

        if [[ $found -eq 0 ]]; then
            echo "❌ bfshell não foi detetado nesta execução" | tee -a "$LOG_FILE"
            echo "ℹ️  Verifica manualmente o log: $tmp_output" | tee -a "$LOG_FILE"
        else
            rm -f "$tmp_output"
        fi

        echo "🛑 Sessão tmux encerrada (switchd_${program_name})" | tee -a "$LOG_FILE"
    done
done

echo -e "\n=== Fim das execuções ($(date)) ===" | tee -a "$LOG_FILE"
