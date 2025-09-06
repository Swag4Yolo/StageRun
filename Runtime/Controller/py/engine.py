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
from lib.utils.status import *
# from app import clear_apps_engine_uninstall

# Engine Status = {Uploaded, Compiled, Installed}

#CONSTANTS

RUNNING_ENGINE = "__running__engine__"
RUNNING_SESSION_NAME = "run_switchd"


logger = logging.getLogger("controller")

# Globals set at init
BUILD_DIR_PATH = None
TOOLS_DIR_PATH = None
HW_FLAGS = None

# Managing Engines
ENGINES_DIR_PATH = None
ENGINES_FILE_PATH = None
RUNNING_ENGINE_FILE_PATH = None
engines = {}
running_engine = {}

# Managing Apps
# APPS_DIR_PATH = None
# APPS_FILE_PATH = None
# APP_RUNNING_FILE_PATH = None
# apps = {}
# running_app = {}

# Compiler
p4_native_compiler_path = None
STAGE_RUN_ROOT_PATH = None
# -----------------------
# Initialization
# -----------------------
def init_engine(config):
    """Initialize engine module with config paths."""
    global ENGINES_DIR_PATH, ENGINES_FILE_PATH, engines, BUILD_DIR_PATH, TOOLS_DIR_PATH, HW_FLAGS, p4_native_compiler_path, STAGE_RUN_ROOT_PATH, RUNNING_ENGINE_FILE_PATH, running_engine #\
    # APPS_DIR_PATH, APPS_FILE_PATH, APP_RUNNING_FILE_PATH, APP_RUNNING_FILE_PATH, apps, running_app

    STAGE_RUN_ROOT_PATH = config["stagerun_root"]
    ENGINES_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["engines"]["engines_dir"])
    ENGINES_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["engines"]["tracker_file"])
    RUNNING_ENGINE_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["engines"]["running_engine"])

    # APPS_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["apps_dir"])
    # APPS_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["tracker_file"])
    # APP_RUNNING_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["running_app"])

    BUILD_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["compiler"]["build_dir"])

    TOOLS_DIR_PATH = config["compiler"]["tools_path"]
    HW_FLAGS = config["compiler"].get("hw_flags", "")

    # Engines
    os.makedirs(ENGINES_DIR_PATH, exist_ok=True)
    engines = load_engines()
    running_engine = load_running_engine()
    print("Running Engine")
    print(running_engine)
    logger.info(f"Engine system initialized with dir={ENGINES_DIR_PATH}, tracker={ENGINES_FILE_PATH}")

    # Apps
    # os.makedirs(APPS_DIR_PATH, exist_ok=True)
    # apps = load_apps()
    # running_app = load_running_app()
    # logger.info(f"Engine system initialized with dir={APPS_DIR_PATH}, tracker={APPS_FILE_PATH}")

    # Compiler
    os.makedirs(BUILD_DIR_PATH, exist_ok=True)
    p4_native_compiler_path = f"{TOOLS_DIR_PATH}/p4_build.sh"
    if not os.path.isfile(p4_native_compiler_path):
        logger.error(f"Failed to Initialize Engine, native compiler not found in {TOOLS_DIR_PATH}.")
        exit(1)
        
# -----------------------
# Engines load/save
# -----------------------
# Engines
def load_engines():
    if ENGINES_FILE_PATH and os.path.exists(ENGINES_FILE_PATH):
        try:
            with open(ENGINES_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Tracker file corrupted, resetting...")
            return {}
    return {}

def save_engines(engines):
    with open(ENGINES_FILE_PATH, "w+") as f:
        json.dump(engines, f, indent=2)

def load_running_engine():
    if RUNNING_ENGINE_FILE_PATH and os.path.exists(RUNNING_ENGINE_FILE_PATH):
        try:
            with open(RUNNING_ENGINE_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Running Engine file corrupted, resetting...")
            return {}
    return {}

def save_running_engine(running_engine):
    with open(RUNNING_ENGINE_FILE_PATH, "w+") as f:
        json.dump(running_engine, f, indent=2)


# -----------------------
# Upload Engine
# -----------------------
async def upload_engine(
    zip_file: UploadFile = File(...),
    tag: str = Form(...),
    version: str = Form(...),
    main_file_name: str = Form(...),
    comment: str = Form("")
):
    # global engines_tracker

    engine_key = f"{tag}_v{version}"

    logger.info(f"Received upload request for engine '{engine_key}'")

    if engine_key in engines:
        logger.warning(f"Upload rejected: engine '{tag}' with version v{version} already exists")
        return {"status": "error", "msg": f"Engine '{tag}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"Engine '{tag}' with version v{version} already exists")

    engine_zip_path = os.path.join(ENGINES_DIR_PATH, f"{engine_key}.zip")
    build_path = os.path.join(BUILD_DIR_PATH, f"{engine_key}/")

    with open(engine_zip_path, "wb") as f:
        shutil.copyfileobj(zip_file.file, f)

    with zipfile.ZipFile(engine_zip_path, "r") as zip_ref:
        if main_file_name not in zip_ref.namelist():
            logger.error(f"Main file '{main_file_name}' not found in {engine_zip_path}")
            logger.info(f"Removing Zip File {engine_zip_path}")
            os.remove(engine_zip_path)
            return {"status": "error", "msg": f"{main_file_name} not found in zip"}
            # raise HTTPException(status_code=400, detail=f"{main_file_name} not found in zip")


    engines[engine_key] = {
        "tag": tag,
        "version": version,
        "main_file_name": main_file_name,
        "status": STATUS_UPLOADED,
        "comment": comment,
        "zip_file_path": engine_zip_path,
        "build_path": build_path,
        "timestamp": datetime.now().isoformat()
    }

    save_engines(engines)

    logger.info(f"Engine '{engine_key}' uploaded successfully")

    return {"status": "ok", "msg": f"Engine '{engine_key}' uploaded successfully"}


async def list_engines():
    if len(engines) == 0:
        raise HTTPException(404, "No engines have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    for _, info in engines.items():
        tag = info["tag"]
        version = info["version"]
        status = info.get("status", STATUS_UNKNOWN)
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}

    return grouped

async def compile_engine(tag: str, version: str):
    """
    Compile an uploaded engine by tag.

    Steps:
    1. Check if engine exists in tracker
    2. Skip if already compiled
    3. Unzip engine into builds dir
    4. Rename main P4 file
    5. Compile using external build script
    6. Update tracker with result
    """

    engine_key = f"{tag}_v{version}"

    if engine_key not in engines:
        return {"status": "error", "message": f"Engine '{tag}' with version {version} does not exist."}

    engine_info = engines[engine_key]
    version = engine_info["version"]
    main_file_name = engine_info["main_file_name"]

    if engine_info.get("status") == STATUS_COMPILED:
        return {"message": f"Engine '{tag}' already compiled", "status": STATUS_SKIPPED}

    # --- Prepare build dir ---
    build_path = os.path.join(BUILD_DIR_PATH, f"{tag}_v{version}")
    # os.makedirs(build_path, exist_ok=True)

    # --- Unzip engine ---
    zip_path = os.path.join(ENGINES_DIR_PATH, f"{tag}_v{version}.zip")
    if not os.path.exists(zip_path):
        return {"error": f"Engine zip file not found: {zip_path}"}

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(build_path)

    # --- Rename main P4 file ---
    src_main_path = os.path.join(build_path, main_file_name)
    dst_main_path = os.path.join(build_path, f"{tag}_v{version}.p4")

    if not os.path.exists(src_main_path):
        return {"error": f"Main P4 file '{main_file_name}' not found in zip"}

    shutil.move(src_main_path, dst_main_path)

    # --- Compile ---
    log_path = os.path.join(build_path, "compile.log")
    # program_name = f"{tag}_v{version}"


    print("HW_FLAGS")
    print(HW_FLAGS)
    cmd = [
        "time",
        os.path.join(TOOLS_DIR_PATH, "p4_build.sh"),
        "-p", dst_main_path,
        # f"P4PPFLAGS={HW_FLAGS}"
    ]

    env = os.environ.copy()
    env["P4PPFLAGS"] = HW_FLAGS

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=build_path,
                check=False
            )
        if result.returncode == 0:
            engines[engine_key]["status"] = STATUS_COMPILED
            with open(ENGINES_FILE_PATH, "w") as f:
                json.dump(engines, f, indent=2)
            return {"message": f"Engine '{tag}' compiled successfully", "status": "COMPILED"}
        else:
            engines[engine_key]["status"] = STATUS_COMPILE_ERROR
            with open(ENGINES_FILE_PATH, "w") as f:
                json.dump(engines, f, indent=2)

            with open(log_path, 'r') as f:
                log_content = f.read()
            return {
                "error": f"Compilation failed for engine '{tag}'",
                "status": STATUS_COMPILE_ERROR,
                "log_path": log_path,
                "log": log_content,
            }
    except Exception as e:
        return {"error": str(e), "status": STATUS_COMPILE_EXCEPTION}


async def install_engine(tag: str, version: str):
    """
        Install Engine:
            - Receives a Tag and Version of an Engine
            - Runs that Engine, initializing the run_switchd (loader)
    """

    engine_key = f"{tag}_v{version}"
    if engine_key not in engines:
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    if engines[engine_key]["status"] != STATUS_COMPILED:
        return {"status": "error", "message": f"Engine {engine_key} is not compiled."}

    # Ensure no other engine is installed
    if RUNNING_ENGINE in engines and not engines[RUNNING_ENGINE]["engine_key"] == "":
        return {"status": "error", "message": f"Another engine ({engines[RUNNING_ENGINE]}) is already installed."}


    # Run switchd
    program_name = engine_key
    log_path = os.path.join(ENGINES_DIR_PATH, f"{RUNNING_ENGINE}.log")

    sde_path = os.environ.get("SDE")  # get $SDE
    if not sde_path:
        raise RuntimeError("SDE environment variable is not set!")


    run_switchd = os.path.join(sde_path, "run_switchd.sh")
        
    # 1. Create a new tmux session detached
    subprocess.run(["tmux", "new", "-d", "-s", RUNNING_SESSION_NAME])

    # 2. Start logging the session output
    subprocess.run(["tmux", "pipe-pane", "-t", RUNNING_SESSION_NAME, f"cat >> {log_path}"])

    # 3. Send the command to tmux
    subprocess.run(["tmux", "send-keys", "-t", RUNNING_SESSION_NAME, f"sudo {run_switchd} -p {program_name}", "C-m"])

    # since process is running proc.returncode will be None (not 0 or 1) because the process hasn’t finished yet.

    # It takes around 13s to initalize so we need to wait
    for _ in range(4):
        time.sleep(5)
        with open(log_path, "r") as f:
                log_content = f.read()
        if "WARNING: Authorised Access Only" in log_content:
            break

    if "WARNING: Authorised Access Only" in log_content:
    # if proc.returncode == 0:
        # Update tracker
        running_engine[RUNNING_ENGINE] = {
            "engine_key": engine_key,
            "log": log_path,
            "program_ids": {},
            "free_pids": [],
        }
        # engines[RUNNING_ENGINE]["engine_key"] = engine_key
        # engines[RUNNING_ENGINE]["pid"] = proc.pid
        # engines[RUNNING_ENGINE]["log"] = log_path
        engines[engine_key]["status"] = STATUS_INSTALLED
        save_engines(engines)
        save_running_engine(running_engine)
        return {"status": "ok", "message":f"Engine {engine_key} Installed Successfully"}

    else:
        # with open(log_path, "r") as f:
        #     log_content = f.read()
        return {"status": "error", 
                "log_path": log_path, 
                "log":log_content
                }

async def uninstall_engine():

    if running_engine[RUNNING_ENGINE]["engine_key"] == "":
        return {"status": "error", "message": f"There it not an Engine Installed."}

    engine_key = running_engine[RUNNING_ENGINE]["engine_key"]
    # pid = running_engine[RUNNING_ENGINE].get("pid")
    # if pid:
    #     try:
    #         os.kill(pid, signal.SIGKILL)
    #     except ProcessLookupError:
    #         return {"status": "warning", "message": f"Process {pid} not found."}

    subprocess.run(["tmux", "kill-session", "-t", RUNNING_SESSION_NAME])
    
    engines[engine_key]["status"] = STATUS_COMPILED
    running_engine[RUNNING_ENGINE]["engine_key"] = ""
    running_engine[RUNNING_ENGINE]["log"] = ""

    save_engines(engines)
    save_running_engine(running_engine)
    # clear_apps_engine_uninstall()

    return {"status": "ok", "message": f"Engine {engine_key} uninstalled."}


async def remove_engine(tag: str, version: str):

    engine_key = f"{tag}_v{version}"
    if engine_key not in engines:
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    if engines[engine_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed engine."}

    # Delete files
    zip_path = os.path.join(ENGINES_DIR_PATH, f"{engine_key}.zip")
    build_path = os.path.join(BUILD_DIR_PATH, f"{engine_key}/")

    Path(zip_path).unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)

    # Remove from tracker
    engines.pop(engine_key, None)
    save_engines(engines)

    return {"status": "ok", "message": f"Engine {engine_key} removed."}

    ####### Program IDS Management #######
def get_program_id():
    prog_ids = running_engine[RUNNING_ENGINE]["program_ids"]
    free_pids = running_engine[RUNNING_ENGINE].setdefault("free_pids", [])

    if free_pids:
        pid = free_pids.pop(0)  # reuse a freed ID
    else:
        # allocate next available ID (1, 2, 3, …)
        used_ids = set(map(int, prog_ids.keys()))
        pid = 1
        while pid in used_ids:
            pid += 1

    return pid

def set_program_id(pid, app_key):
    running_engine[RUNNING_ENGINE]["program_ids"][str(pid)] = app_key
    save_running_engine(running_engine)

def remove_program_id(pid):
    pid_str = str(pid)
    if pid_str in running_engine[RUNNING_ENGINE]["program_ids"]:
        del running_engine[RUNNING_ENGINE]["program_ids"][pid_str]
        running_engine[RUNNING_ENGINE].setdefault("free_pids", []).append(pid)
    save_running_engine(running_engine)


def clear_program_ids():
    running_engine[RUNNING_ENGINE]["program_ids"] = {}
    running_engine[RUNNING_ENGINE]["free_pids"] = []
    save_running_engine(running_engine)
