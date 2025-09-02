import os
import shutil
import zipfile
import json
import logging
import subprocess
import signal
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException, File
from pathlib import Path
import time
from status import *

logger = logging.getLogger("controller")

# App Status = {Uploaded, Installed, Running}

# Managing Apps
APPS_DIR_PATH = None
APPS_FILE_PATH = None
APP_RUNNING_FILE_PATH = None
apps = {}
running_app = {}

# -----------------------
# Initialization
# -----------------------
def init_app(config):
    """Initialize app module with config paths."""
    global \
    APPS_DIR_PATH, APPS_FILE_PATH, APP_RUNNING_FILE_PATH, APP_RUNNING_FILE_PATH, apps, running_app

    STAGE_RUN_ROOT_PATH = config["stagerun_root"]

    APPS_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["apps_dir"])
    APPS_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["tracker_file"])
    APP_RUNNING_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["running_app"])

    # Apps
    os.makedirs(APPS_DIR_PATH, exist_ok=True)
    apps = load_apps()
    running_app = load_running_app()
    logger.info(f"App system initialized with dir={APPS_DIR_PATH}, tracker={APPS_FILE_PATH}")

        
def load_apps():
    if APPS_FILE_PATH and os.path.exists(APPS_FILE_PATH):
        try:
            with open(APPS_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Running App file corrupted, resetting...")
            return {}
    return {}

def save_apps(apps):
    with open(APPS_FILE_PATH, "w+") as f:
        json.dump(apps, f, indent=2)

def load_running_app():
    if APP_RUNNING_FILE_PATH and os.path.exists(APP_RUNNING_FILE_PATH):
        try:
            with open(APP_RUNNING_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Running App file corrupted, resetting...")
            return {}
    return {}

def save_running_app(running_app):
    with open(APP_RUNNING_FILE_PATH, "w+") as f:
        json.dump(running_app, f, indent=2)



async def upload_app(
    app_file: UploadFile = File(...),
    tag: str = Form(...),
    version: str = Form(...),
    comment: str = Form("")
):
    app_key = f"{tag}_v{version}"

    logger.info(f"Received upload request for App '{app_key}'")

    if app_key in apps:
        logger.warning(f"Upload rejected: app '{app_key}' with version v{version} already exists")
        return {"status": "error", "msg": f"App '{app_key}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"App '{tag}' with version v{version} already exists")

    _, ext = os.path.splitext(app_file.filename)
    if not ext or ext != '.py':  # fallback if no extension provided
        ext = ".bin"
        return {"status": "error", "msg": f"The provided {app_file.filename} does not have a supported extension"}
    
    print(ext)
    app_path = os.path.join(APPS_DIR_PATH, f"{app_key}{ext}")
    print(app_path)

    with open(app_path, "wb") as f:
        shutil.copyfileobj(app_file.file, f)

    apps[app_key] = {
        "tag": tag,
        "version": version,
        "status": "UPLOADED",
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
        "app_path": app_path
    }

    save_apps(apps)

    logger.info(f"App '{app_key}' uploaded successfully")

    return {"status": "ok", "msg": f"App '{app_key}' uploaded successfully"}


async def list_apps():
    if len(apps) == 0:
        raise HTTPException(404, "No apps have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    for _, info in apps.items():
        tag = info["tag"]
        version = info["version"]
        status = info.get("status", "UNKNOWN")
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}

    return grouped


# async def install_app(tag: str, version: str):

#     app_key = f"{tag}_v{version}"
#     if app_key not in apps:
#         return {"status": "error", "message": f"App {app_key} not found."}

#     if apps[app_key]["status"] == "INSTALLED":
#         return {"status": "error", "message": f"App {app_key} already installed."}
    
#     if apps[app_key]["status"] == "RUNNING":
#         return {"status": "error", "message": f"App {app_key} is already installed and running."}

#     # Ensure no other app is installed
#     if RUNNING_ENGINE in engines and not engines[RUNNING_ENGINE]["app_key"] == "":
#         return {"status": "error", "message": f"Another app ({engines[RUNNING_ENGINE]}) is already installed."}


#     # Run switchd
#     program_name = app_key
#     log_path = os.path.join(ENGINES_DIR_PATH, f"{RUNNING_ENGINE}.log")

#     sde_path = os.environ.get("SDE")  # get $SDE
#     if not sde_path:
#         raise RuntimeError("SDE environment variable is not set!")


#     run_switchd = os.path.join(sde_path, "run_switchd.sh")
        
#     # 1. Create a new tmux session detached
#     subprocess.run(["tmux", "new", "-d", "-s", RUNNING_SESSION_NAME])

#     # 2. Start logging the session output
#     subprocess.run(["tmux", "pipe-pane", "-t", RUNNING_SESSION_NAME, f"cat >> {log_path}"])

#     # 3. Send the command to tmux
#     subprocess.run(["tmux", "send-keys", "-t", RUNNING_SESSION_NAME, f"sudo {run_switchd} -p {program_name}", "C-m"])

#     # since process is running proc.returncode will be None (not 0 or 1) because the process hasn’t finished yet.

#     # It takes around 13s to initalize so we need to wait
#     for _ in range(4):
#         time.sleep(5)
#         with open(log_path, "r") as f:
#                 log_content = f.read()
#         if "WARNING: Authorised Access Only" in log_content:
#             break

#     if "WARNING: Authorised Access Only" in log_content:
#     # if proc.returncode == 0:
#         # Update tracker
#         running_engine[RUNNING_ENGINE] = {
#             "app_key": app_key,
#             "log": log_path,
#         }
#         # engines[RUNNING_ENGINE]["app_key"] = app_key
#         # engines[RUNNING_ENGINE]["pid"] = proc.pid
#         # engines[RUNNING_ENGINE]["log"] = log_path
#         engines[app_key]["status"] = "INSTALLED"
#         save_engines(engines)
#         save_running_engine(running_engine)
#         return {"status": "ok", "message":f"App {app_key} Installed Successfully"}

#     else:
#         # with open(log_path, "r") as f:
#         #     log_content = f.read()
#         return {"status": "error", 
#                 "log_path": log_path, 
#                 "log":log_content
#                 }


async def remove_app(tag: str, version: str):

    app_key = f"{tag}_v{version}"
    if app_key not in apps:
        return {"status": "error", "message": f"Engine {app_key} not found."}

    if apps[app_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed app."}
    
    if apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": "Cannot remove a running app."}

    # Delete files

    Path(apps[app_key]["app_path"]).unlink(missing_ok=True)
    # shutil.rmtree(build_path, ignore_errors=True)

    # Remove from tracker
    apps.pop(app_key, None)
    save_apps(apps)

    return {"status": "ok", "message": f"App {app_key} removed."}
