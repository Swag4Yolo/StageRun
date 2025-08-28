#!/bin/bash

CONTROLLER_ENV="controller_env"

cd server

echo "Initializing Controller Environment"
    python3 -m venv $CONTROLLER_ENV
    source ${CONTROLLER_ENV}/bin/activate
    pip3 install -r requirements.txt

echo "Initializing Program"
    python3 controller.py

cd ..