#!/bin/bash

VENV="client_env"
PROGRAM="client.py"

cd py

echo "Initializing ${VENV} Environment"
    python3 -m venv $VENV
    source ${VENV}/bin/activate
    pip3 install -r requirements.txt

echo "Initializing Client"
    python3 ${PROGRAM}

cd ..