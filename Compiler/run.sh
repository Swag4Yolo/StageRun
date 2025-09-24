#!/bin/bash

VENV="compiler_env"
PROGRAM="py/stagerun_compiler.py"
PROGRAMS_DIR="Programs"

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
            python3 "${PROGRAM}" "${file}" -o "${dir_path}/${filename}.out" #> "${PROGRAMS_DIR}/${filename}.log"
        fi
    fi
done

deactivate