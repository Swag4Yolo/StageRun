import os
import shutil
import zipfile
import logging
import subprocess
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException, File
from pathlib import Path
import time

# Custom imports
from lib.utils.status import *
import lib.controller.state_manager as sm

logger = logging.getLogger("controller")



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

    if engine_key in sm.engines:
        logger.warning(f"Upload rejected: engine '{tag}' with version v{version} already exists")
        return {"status": "error", "msg": f"Engine '{tag}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"Engine '{tag}' with version v{version} already exists")

    engine_zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}.zip")
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{engine_key}/")

    with open(engine_zip_path, "wb") as f:
        shutil.copyfileobj(zip_file.file, f)

    with zipfile.ZipFile(engine_zip_path, "r") as zip_ref:
        if main_file_name not in zip_ref.namelist():
            logger.error(f"Main file '{main_file_name}' not found in {engine_zip_path}")
            logger.info(f"Removing Zip File {engine_zip_path}")
            os.remove(engine_zip_path)
            return {"status": "error", "msg": f"{main_file_name} not found in zip"}
            # raise HTTPException(status_code=400, detail=f"{main_file_name} not found in zip")


    sm.engines[engine_key] = {
        "tag": tag,
        "version": version,
        "main_file_name": main_file_name,
        "status": STATUS_UPLOADED,
        "comment": comment,
        "zip_file_path": engine_zip_path,
        "build_path": build_path,
        "timestamp": datetime.now().isoformat()
    }

    sm.save_engines()

    logger.info(f"Engine '{engine_key}' uploaded successfully")

    return {"status": "ok", "msg": f"Engine '{engine_key}' uploaded successfully"}

async def list_engines():
    if len(sm.engines) == 0:
        raise HTTPException(404, "No engines have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    for _, info in sm.engines.items():
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

    if engine_key not in sm.engines:
        return {"status": "error", "message": f"Engine '{tag}' with version {version} does not exist."}

    engine_info = sm.engines[engine_key]
    version = engine_info["version"]
    main_file_name = engine_info["main_file_name"]

    if engine_info.get("status") == STATUS_COMPILED:
        return {"message": f"Engine '{tag}' already compiled", "status": STATUS_SKIPPED}

    # --- Prepare build dir ---
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{tag}_v{version}")
    # os.makedirs(build_path, exist_ok=True)

    # --- Unzip engine ---
    zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{tag}_v{version}.zip")
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
    #TODO: delete file? What 
    # program_name = f"{tag}_v{version}"


    # print("HW_FLAGS")
    print(sm.HW_FLAGS)
    cmd = [
        "time",
        os.path.join(sm.TOOLS_DIR_PATH, "p4_build.sh"),
        "-p", dst_main_path,
        # f"P4PPFLAGS={HW_FLAGS}"
    ]

    env = os.environ.copy()
    env["P4PPFLAGS"] = sm.HW_FLAGS

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
            sm.engines[engine_key]["status"] = STATUS_COMPILED
            sm.save_engines()
            return {"message": f"Engine '{tag}' compiled successfully", "status": "COMPILED"}
        else:
            sm.engines[engine_key]["status"] = STATUS_COMPILE_ERROR
            sm.save_engines()

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
    if engine_key not in sm.engines:
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    if sm.engines[engine_key]["status"] != STATUS_COMPILED:
        return {"status": "error", "message": f"Engine {engine_key} is not compiled."}

    # Ensure no other engine is installed
    if sm.RUNNING_ENGINE in sm.engines and not sm.engines[sm.RUNNING_ENGINE]["engine_key"] == "":
        return {"status": "error", "message": f"Another engine ({sm.engines[sm.RUNNING_ENGINE]}) is already installed."}


    # Run switchd
    program_name = engine_key
    log_path = os.path.join(sm.ENGINES_DIR_PATH, f"{sm.RUNNING_ENGINE}.log")

    sde_path = os.environ.get("SDE")  # get $SDE
    if not sde_path:
        raise RuntimeError("SDE environment variable is not set!")


    run_switchd = os.path.join(sde_path, "run_switchd.sh")
        
    # 1. Create a new tmux session detached
    subprocess.run(["tmux", "new", "-d", "-s", sm.RUNNING_SESSION_NAME])

    # 2. Start logging the session output
    subprocess.run(["tmux", "pipe-pane", "-t", sm.RUNNING_SESSION_NAME, f"cat >> {log_path}"])

    # 3. Send the command to tmux
    # Note we need to cd, because when the directory fails to exist for an undiscovered reason yet, tofino bfrt_python tries to do os.getcwd(), which fails to get a directory
    subprocess.run(["tmux", "send-keys", "-t", sm.RUNNING_SESSION_NAME, f"cd; sudo {run_switchd} -p {program_name}", "C-m"])

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
        sm.running_engine[sm.RUNNING_ENGINE] = {
            "engine_key": engine_key,
            "log": log_path,
            "program_ids": {},
            "free_pids": [],
        }
        # engines[RUNNING_ENGINE]["engine_key"] = engine_key
        # engines[RUNNING_ENGINE]["pid"] = proc.pid
        # engines[RUNNING_ENGINE]["log"] = log_path
        sm.engines[engine_key]["status"] = STATUS_INSTALLED
        sm.save_engines()
        sm.save_running_engine()

        # Connect to Tofino and Init Configurations
        sm.connect_tofino()
        sm.engine_controller._init_configs_()

        return {"status": "ok", "message":f"Engine {engine_key} Installed Successfully"}

    else:
        # with open(log_path, "r") as f:
        #     log_content = f.read()
        return {"status": "error", 
                "log_path": log_path, 
                "log":log_content
                }

async def uninstall_engine():
    if sm.running_engine[sm.RUNNING_ENGINE]["engine_key"] == "":
        return {"status": "error", "message": f"There it not an Engine Installed."}

    engine_key = sm.running_engine[sm.RUNNING_ENGINE]["engine_key"]
    # pid = running_engine[RUNNING_ENGINE].get("pid")
    # if pid:
    #     try:
    #         os.kill(pid, signal.SIGKILL)
    #     except ProcessLookupError:
    #         return {"status": "warning", "message": f"Process {pid} not found."}

    subprocess.run(["tmux", "kill-session", "-t", sm.RUNNING_SESSION_NAME])
    
    sm.engines[engine_key]["status"] = STATUS_COMPILED
    sm.running_engine[sm.RUNNING_ENGINE]["engine_key"] = ""
    sm.running_engine[sm.RUNNING_ENGINE]["log"] = ""

    sm.save_engines()
    sm.save_running_engine()

    sm.clear_apps()
    sm.disconnect_tofino()
    return {"status": "ok", "message": f"Engine {engine_key} uninstalled."}


async def remove_engine(tag: str, version: str):
    engine_key = f"{tag}_v{version}"
    if engine_key not in sm.engines:
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    if sm.engines[engine_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed engine."}

    # Delete files
    zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}.zip")
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{engine_key}/")

    Path(zip_path).unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)

    # Remove from tracker
    sm.engines.pop(engine_key, None)
    sm.save_engines()

    return {"status": "ok", "message": f"Engine {engine_key} removed."}

        
####### Program IDS Management #######
        
def get_program_id():
    prog_ids = sm.running_engine[sm.RUNNING_ENGINE]["program_ids"]
    free_pids = sm.running_engine[sm.RUNNING_ENGINE].setdefault("free_pids", [])

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
    sm.running_engine[sm.RUNNING_ENGINE]["program_ids"][str(pid)] = app_key
    sm.save_running_engine(sm.running_engine)

def remove_program_id(pid):
    pid_str = str(pid)
    if pid_str in sm.running_engine[sm.RUNNING_ENGINE]["program_ids"]:
        del sm.running_engine[sm.RUNNING_ENGINE]["program_ids"][pid_str]
        sm.running_engine[sm.RUNNING_ENGINE].setdefault("free_pids", []).append(pid)
    sm.save_running_engine(sm.running_engine)


def clear_program_ids():
    sm.running_engine[sm.RUNNING_ENGINE]["program_ids"] = {}
    sm.running_engine[sm.RUNNING_ENGINE]["free_pids"] = []
    sm.save_running_engine(sm.running_engine)


