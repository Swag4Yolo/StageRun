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
            python3 "${PROGRAM}" "${file}" -o "${dir_path}/${filename}.out" > "${dir_path}/${filename}.log" 2>&1
        fi
    fi
done

deactivate

# 3. Disable tracing and restore stdout/stderr (optional but good practice)
# set +x
exec 1>&3 3>&-