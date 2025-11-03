#!/bin/bash

VENV="compiler_env"
PROGRAM="py/stagerun_compiler.py"
PROGRAMS_DIR="Programs"
LOG_FILE="compiler.log"


# Remove old log
rm -rf ${LOG_FILE}
# 1. Redirect file descriptor 3 (a custom one) to the log file
exec 3>&1 1>>"${LOG_FILE}" 2>&1

# 2. Enable execution tracing. All commands will now be written to stderr,
#    which is redirected to the log file via 2>&1.
# set -x



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
            for run_idx in {1..10}; do
                echo -e "\t\t Run ${run_idx}/10 => python3 ${PROGRAM}"
                if time_output=$( { time -p python3 "${PROGRAM}" "${file}" -o "${program_path}"; } 2>&1 ); then
                    command_log=$(printf '%s\n' "$time_output" | sed '/^real /d;/^user /d;/^sys /d;')
                    if [ -n "$command_log" ]; then
                        printf '%s\n' "$command_log"
                    fi
                    real_time=$(printf '%s\n' "$time_output" | awk '/^real / {print $2}' | tail -n 1)
                    if [ -n "$real_time" ]; then
                        echo -e "\t\t real_time=${real_time}s"
                    fi
                else
                    echo -e "\t\t Compilation failed => ${filename}"
                    printf '%s\n' "$time_output"
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

# 3. Disable tracing and restore stdout/stderr (optional but good practice)
# set +x
exec 1>&3 3>&-
