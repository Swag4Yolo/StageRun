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
from lib.controller.types import Engine
from lib.utils.status import *
import lib.controller.state_manager as sm

logger = logging.getLogger("controller")



async def upload_engine(
    zip_file: UploadFile = File(...),
    engine_isa: UploadFile = File(...),
    tag: str = Form(...),
    version: str = Form(...),
    main_file_name: str = Form(...),
    comment: str = Form("")
):
    engine_key = sm.get_engine_key(tag, version)

    logger.info(f"Received upload request for engine '{engine_key}'")

    if sm.exists_engine(engine_key):
        logger.warning(f"Upload rejected: engine '{tag}' with version v{version} already exists")
        return {"status": "error", "msg": f"Engine '{tag}' with version v{version} already exists"}

    engine_zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}.zip")
    engine_isa_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}_isa.json")
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{engine_key}/")

    # Save zip file
    with open(engine_zip_path, "wb") as f:
        shutil.copyfileobj(zip_file.file, f)

    # Save ISA file
    with open(engine_isa_path, "wb") as f:
        shutil.copyfileobj(engine_isa.file, f)

    # Verify main_file_name inside zip
    with zipfile.ZipFile(engine_zip_path, "r") as zip_ref:
        if main_file_name not in zip_ref.namelist():
            logger.error(f"Main file '{main_file_name}' not found in {engine_zip_path}")
            logger.info(f"Removing files {engine_zip_path} and {engine_isa_path}")
            os.remove(engine_isa_path)
            os.remove(engine_zip_path)
            return {"status": "error", "msg": f"{main_file_name} not found in zip"}

    sm.add_engine(
        Engine(
            engine_key=engine_key,
            tag=tag,
            version=version,
            main_file_name=main_file_name,
            status=STATUS_UPLOADED,
            comment=comment,
            zip_path=engine_zip_path,
            isa_path=engine_isa_path,
            build_path=build_path,
            timestamp=datetime.now().isoformat(),
            recirc_ports={})
        )

    logger.info(f"Engine '{engine_key}' uploaded successfully")

    return {"status": "ok", "msg": f"Engine '{engine_key}' uploaded successfully"}


async def list_engines():
    if len(sm.engines) == 0:
        raise HTTPException(404, "No engines have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    engines = sm.get_engines()
    for engine in engines:
        tag = engine.tag
        version = engine.version
        status = engine.status
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}

    return grouped

def check_flags(flags: list[str]) -> tuple[bool, str]:
    """
    Validate flags:
    - If 'HW' is present, all RECIR_PORT_P{0..3} must also be present.
    """
    if "HW" in flags:
        required = {"RECIR_PORT_P0", "RECIR_PORT_P1", "RECIR_PORT_P2", "RECIR_PORT_P3"}
        present = {f.split("=")[0] for f in flags}
        missing = required - present
        if missing:
            return False, f"Missing mandatory flags when HW is enabled: {', '.join(sorted(missing))}"
    return True, ""


async def compile_engine(tag: str, version: str, flags: str = ""):
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

    engine_key = sm.get_engine_key(tag, version)

    if not sm.exists_engine(engine_key):
        return {"status": "error", "message": f"Engine '{tag}' with version {version} does not exist."}

    engine = sm.get_engine(engine_key)

    if engine.status == STATUS_COMPILED:
        return {"message": f"Engine '{tag}' already compiled", "status": STATUS_SKIPPED}
    
    # engine_info = sm.engines[engine_key]
    # version = engine_info["version"]
    # main_file_name = engine_info["main_file_name"]

    # if engine_info.get("status") == STATUS_COMPILED:
    #     return {"message": f"Engine '{tag}' already compiled", "status": STATUS_SKIPPED}

    # --- Parse flags ---
    flag_list = flags.split() if flags else []
    ok, msg = check_flags(flag_list)
    if not ok:
        return {"status": "error", "message": msg}

    # Updated Recirc Ports to the engine 
    recirc_ports = {}
    # print("flag_list")
    # print(flag_list)
    for flag in flag_list:
        if 'RECIR_P' in flag:
            splits = flag.split('=')
            recirc_ports[splits[0]] = f"{splits[1]}/-"

    # print("Recirc Ports")
    # print(recirc_ports)

    # Convert to "-D FLAG" form
    ppflags = " ".join([f"-D {flag}" for flag in flag_list])

    # print("ppflags")
    # print(ppflags)

    # --- Prepare build dir ---
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{engine_key}")
    # os.makedirs(build_path, exist_ok=True)

    # --- Unzip engine ---
    zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}.zip")
    if not os.path.exists(zip_path):
        return {"error": f"Engine zip file not found: {zip_path}"}

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(build_path)

    # --- Rename main P4 file ---
    src_main_path = os.path.join(build_path, engine.main_file_name)
    dst_main_path = os.path.join(build_path, f"{engine_key}.p4")

    if not os.path.exists(src_main_path):
        return {"error": f"Main P4 file '{engine.main_file_name}' not found in zip"}

    shutil.move(src_main_path, dst_main_path)

    # --- Compile ---
    log_path = os.path.join(build_path, "compile.log")
    #TODO: delete file? What 
    # program_name = f"{tag}.v{version}"


    cmd = [
        "time",
        os.path.join(sm.TOOLS_DIR_PATH, "p4_build.sh"),
        "-p", dst_main_path,
        f"P4PPFLAGS={ppflags}"
    ]

    env = os.environ.copy()
    # env["P4PPFLAGS"] = sm.HW_FLAGS

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
            engine.status = STATUS_COMPILED
            engine.recirc_ports = recirc_ports
            sm.update_engine(engine)
            # sm.engines[engine_key]["status"] = STATUS_COMPILED
            # sm.engines[engine_key]["recirc_ports"] = recirc_ports
            # sm.save_engines()
            return {"message": f"Engine '{tag}' version {version} compiled successfully", "status": "COMPILED"}
        else:
            engine.status = STATUS_COMPILE_ERROR
            sm.update_engine(engine)
            # sm.engines[engine_key]["status"] = STATUS_COMPILE_ERROR
            # sm.save_engines()

            with open(log_path, 'r') as f:
                log_content = f.read()
            return {
                "error": f"Compilation failed for engine '{tag}' version {version}",
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

    engine_key = sm.get_engine_key(tag, version)
    if not sm.exists_engine(engine_key):
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    engine = sm.get_engine(engine_key)

    if engine.status != STATUS_COMPILED:
        return {"status": "error", "message": f"Engine {engine_key} is not compiled."}

    # Ensure no other engine is installed
    # if sm.RUNNING_ENGINE in sm.engines and not sm.engines[sm.RUNNING_ENGINE]["engine_key"] == "":
    if sm.is_an_engine_running():
        return {"status": "error", "message": f"Another engine ({sm.get_running_engine_key()}) is already installed."}


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
        sm.set_running_engine(engine_key, log_path)
        sm.set_engine_status(engine_key, STATUS_INSTALLED)

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
    
    if not sm.is_an_engine_running():
        return {"status": "error", "message": f"There it not an Engine Installed."}

    engine_key = sm.get_running_engine_key()

    subprocess.run(["tmux", "kill-session", "-t", sm.RUNNING_SESSION_NAME])
    
    sm.set_engine_status(engine_key, STATUS_COMPILED)
    sm.reset_running_engine()

    sm.clear_apps()
    sm.clear_port_sets()
    sm.disconnect_tofino()
    return {"status": "ok", "message": f"Engine {engine_key} uninstalled."}


async def remove_engine(tag: str, version: str):
    engine_key = sm.get_engine_key(tag, version)
    if not sm.exists_engine(engine_key):
        return {"status": "error", "message": f"Engine {engine_key} not found."}

    engine = sm.get_engine(engine_key)

    if engine.status == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed engine."}

    # Delete files
    zip_path = os.path.join(sm.ENGINES_DIR_PATH, f"{engine_key}.zip")
    build_path = os.path.join(sm.BUILD_DIR_PATH, f"{engine_key}/")

    Path(zip_path).unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)

    # Remove from tracker
    sm.delete_engine(engine_key)

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


