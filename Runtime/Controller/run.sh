#!/bin/bash

VENV="controller_env"
PROGRAM="controller.py"

cd py

echo "Initializing Controller Environment"
    python3 -m venv $VENV
    source ${VENV}/bin/activate
    pip3 install -r requirements.txt
echo "Initializing Program"
    python3 ${PROGRAM}
    # python3 ${PROGRAM} 2>&1 > controller.log
cd ..