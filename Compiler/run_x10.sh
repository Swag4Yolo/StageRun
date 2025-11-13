#!/bin/bash

VENV="compiler_env"
PROGRAM="py/stagerun_compiler.py"
PROGRAMS_DIR="Programs"
LOG_FILE="compiler.log"

: > "${LOG_FILE}"

# Major Script
cd py

echo "Initializing ${VENV} Environment"
    python3 -m venv $VENV
    source ${VENV}/bin/activate
    pip3 install -r requirements.txt

cd ..

echo "Removing old Compiled Files"
    rm -rf ${PROGRAMS_DIR}/**/*.out
    rm -rf ${PROGRAMS_DIR}/**/*.log

echo "Compiling Programs"

for file in "${PROGRAMS_DIR}"/**/*.srun; do

    # Verificamos se o item é um ficheiro (para evitar subpastas)
    if [ -f "$file" ]; then

        full_name=$(basename -- "$file")
        filename="${full_name%.*}"
        extension="${full_name##*.}"
        dir_path=$(dirname -- "$file")

        if [[ "$extension" == "srun" ]]; then 
            echo -e "\t Compiling Program => ${filename}"
            program_path="${dir_path}/${filename}.out"
            run_success=true
            printf 'program=%s\n' "${file}" >> "${LOG_FILE}"
            for run_idx in {1..10}; do
                echo -e "\t\t Run ${run_idx}/10 => python3 ${PROGRAM}"
                time_output=$( { time -p python3 "${PROGRAM}" "${file}" -o "${program_path}"; } 2>&1 )
                command_status=$?
                command_log=$(printf '%s\n' "$time_output" | sed '/^real /d;/^user /d;/^sys /d;')
                if [ -n "$command_log" ]; then
                    printf '%s\n' "$command_log"
                fi
                real_time=$(printf '%s\n' "$time_output" | awk '/^real / {print $2}' | tail -n 1)
                if [ -n "$real_time" ]; then
                    echo -e "\t\t real_time=${real_time}s"
                fi
                if [ "$command_status" -ne 0 ]; then
                    echo -e "\t\t Compilation failed => ${filename}"
                fi
                status_label=$([ "$command_status" -eq 0 ] && printf 'success' || printf 'failure')
                printf '%s %s\n' "${real_time:-N/A}" "${status_label}" >> "${LOG_FILE}"
                if [ "$command_status" -ne 0 ]; then
                    run_success=false
                    break
                fi
            done
            if [ "$run_success" = true ]; then
                chmod +x "${program_path}"
            fi
        fi
    fi
done

deactivate
