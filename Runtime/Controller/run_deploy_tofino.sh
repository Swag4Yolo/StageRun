#!/bin/bash
set -e

CONTROLLER_VERSION="v1.0"
TUNNEL_SSH_ENTITY="onitof"
TUNNEL_HOST="localhost"
TUNNEL_PORT=1337
ZIP_DIR="/home/tofino/Work/PhD/StageRun/Runtime"
ZIP_NAME="controller_${CONTROLLER_VERSION}.zip"

echo "Zipping Controller"
zip -r ${ZIP_NAME} py/ run.sh config.yaml -x "py/controller_env/*"

echo "Cleaning remote ZIP_DIR and recreating..."
ssh ${TUNNEL_SSH_ENTITY} "rm -rf ${ZIP_DIR} && mkdir -p ${ZIP_DIR}"

echo "Copying Zip To ${TUNNEL_SSH_ENTITY}"
scp ${ZIP_NAME} ${TUNNEL_SSH_ENTITY}:${ZIP_DIR}

echo "Initializing Tunnel (manual run afterwards)..."
ssh -t -L ${TUNNEL_PORT}:${TUNNEL_HOST}:${TUNNEL_PORT} ${TUNNEL_SSH_ENTITY} "
    tmux new -A -s AutoDeployController \; \
    send-keys 'cd ${ZIP_DIR}' C-m \; \
    send-keys 'unzip -o ${ZIP_NAME}' C-m \; \
    send-keys 'chmod +x run.sh' C-m \; \
    send-keys './run.sh' C-m
"

    # chmod +x run.sh &&
    # ./run.sh; exec bash