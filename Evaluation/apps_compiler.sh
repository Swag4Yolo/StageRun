#!/bin/bash

# Número de vezes que cada programa será compilado
N_RUNS=10

LOG_FILE="apps_compile.log"
# TOOLS_DIR=/home/tofino/tools
TOOLS_DIR=/home/docker/tools
# Limpa o log anterior
> "$LOG_FILE"

# === LISTA DE PROGRAMAS ===
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
    # "activermt/activermt/dataplane/active.p4"
    "DANE/NativeP4Apps/Ditto/Tofino1/originalImplementation/p4/traffic_pattern_tofino/p4src/traffic_pattern_tofino.p4"
    
    # ======= Programas =======
    #        SDE 9.7.0 => SDE 9.13.2 (Upgraded)
    # "NetWarden/release/pack_mal/pack_mal.p4"
    

    # ======= Frameworks =======
    #        SDE 9.13.2
    # "P4runpro/custom/p4src/p4runpro.p4"



    # ======= Frameworks =======
    #        SDE 9.7.0
)

# === FLAGS ESPECÍFICAS PARA ALGUNS PROGRAMAS ===
declare -A P4_FLAGS
P4_FLAGS["P4runpro/custom/p4src/p4runpro.p4"]='-Xp4c=--traffic-limit=98'
# P4_FLAGS["DANE/NativeP4Apps/Ditto/Tofino1/originalImplementation/p4/traffic_pattern_tofino/p4src/traffic_pattern_tofino.p4"]='-Xp4c=--disable-parse-depth-limit'
# P4_FLAGS["activermt/activermt/dataplane/active.p4"]='-Xp4c=--traffic-limit=80'

echo "=== Início da compilação ($(date)) ===" | tee -a "$LOG_FILE"
echo "Cada programa será compilado $N_RUNS vez(es)" | tee -a "$LOG_FILE"

for program in "${P4_PROGRAMS[@]}"; do
    echo -e "\n---------------------------------------------" | tee -a "$LOG_FILE"
    echo "Programa: $program" | tee -a "$LOG_FILE"

    if [[ ! -f "$program" ]]; then
        echo "⚠️  ERRO: Ficheiro não encontrado: $program" | tee -a "$LOG_FILE"
        continue
    fi

    # Verifica flags específicas
    EXTRA_FLAGS="P4FLAGS=\"${P4_FLAGS[$program]}\""
    if [[ -n "$EXTRA_FLAGS" ]]; then
        echo "Usando flags extra: $EXTRA_FLAGS" | tee -a "$LOG_FILE"
    fi

    for ((i=1; i<=N_RUNS; i++)); do
        echo -e "\n🔁 Execução $i de $N_RUNS - $(date)" | tee -a "$LOG_FILE"

        # Monta o comando completo de compilação
        CMD="$TOOLS_DIR/p4_build.sh -p $program"
        if [[ -n "$EXTRA_FLAGS" ]]; then
            CMD="$CMD $EXTRA_FLAGS"
        fi

        echo "Comando: $CMD" | tee -a "$LOG_FILE"

        # Executa e mede o tempo
        {
            time bash -c "$CMD"
        } >>"$LOG_FILE" 2>&1

        if [[ $? -eq 0 ]]; then
            echo "✅ Execução $i concluída com sucesso" | tee -a "$LOG_FILE"
        else
            echo "❌ Erro na execução $i" | tee -a "$LOG_FILE"
            continue
        fi
    done
done

echo -e "\n=== Fim da compilação ($(date)) ===" | tee -a "$LOG_FILE"
