import os
import shutil
import zipfile
import json
import logging
import subprocess
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException



# class Engine():
#     def __init__(self, tag="", version="v0.1", main_file_location=None, comment=""):
#         self.tag = tag
#         self.version = version
#         self.main_file_location = main_file_location
#         self.comment = comment

logger = logging.getLogger("controller")

# Globals set at init
ENGINES_DIR_PATH = None
TRACKER_FILE_PATH = None
BUILD_DIR_PATH = None
TOOLS_DIR_PATH = None
HW_FLAGS = None
engines_tracker = {}
p4_native_compiler_path = None
STAGE_RUN_ROOT_PATH = None

# -----------------------
# Initialization
# -----------------------
def init_engine(config):
    """Initialize engine module with config paths."""
    global ENGINES_DIR_PATH, TRACKER_FILE_PATH, engines_tracker, BUILD_DIR_PATH, TOOLS_DIR_PATH, HW_FLAGS, p4_native_compiler_path, STAGE_RUN_ROOT_PATH

    STAGE_RUN_ROOT_PATH = config["stagerun_root"]
    ENGINES_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["engines"]["engines_dir"])
    TRACKER_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["engines"]["tracker_file"])
    BUILD_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["compiler"]["build_dir"])

    TOOLS_DIR_PATH = config["compiler"]["tools_path"]
    HW_FLAGS = config["compiler"].get("hw_flags", "")

    os.makedirs(ENGINES_DIR_PATH, exist_ok=True)
    engines_tracker = load_tracker()
    logger.info(f"Engine system initialized with dir={ENGINES_DIR_PATH}, tracker={TRACKER_FILE_PATH}")

    os.makedirs(BUILD_DIR_PATH, exist_ok=True)

    p4_native_compiler_path = f"{TOOLS_DIR_PATH}/p4_build.sh"
    if not os.path.isfile(p4_native_compiler_path):
        logger.error(f"Failed to Initialize Engine, native compiler not found in {TOOLS_DIR_PATH}.")
        exit(1)
        
# -----------------------
# Tracker load/save
# -----------------------
def load_tracker():
    if TRACKER_FILE_PATH and os.path.exists(TRACKER_FILE_PATH):
        try:
            with open(TRACKER_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Tracker file corrupted, resetting...")
            return {}
    return {}

def save_tracker(tracker):
    if TRACKER_FILE_PATH:
        with open(TRACKER_FILE_PATH, "w") as f:
            json.dump(tracker, f, indent=2)


# -----------------------
# Upload Engine
# -----------------------
async def upload_engine(
    zip_file: UploadFile,
    tag: str = Form(...),
    version: str = Form(...),
    main_file_name: str = Form(...),
    comment: str = Form(None)
):
    # global engines_tracker

    logger.info(f"Received upload request for engine '{tag}' {version}")

    if tag in engines_tracker:
        logger.warning(f"Upload rejected: engine '{tag}' already exists")
        raise HTTPException(status_code=400, detail=f"Engine with tag '{tag}' already exists")

    engine_zip_path = os.path.join(ENGINES_DIR_PATH, f"{tag}_{version}.zip")

    print(engine_zip_path)

    with open(engine_zip_path, "wb") as f:
        shutil.copyfileobj(zip_file.file, f)

    with zipfile.ZipFile(engine_zip_path, "r") as zip_ref:
        if main_file_name not in zip_ref.namelist():
            logger.error(f"Main file '{main_file_name}' not found in {engine_zip_path}")
            logger.info(f"Removing Zip File {engine_zip_path}")
            os.remove(engine_zip_path)
            return {"status": "error", "msg": f"{main_file_name} not found in zip"}

    engines_tracker[tag] = {
        "tag": tag,
        "version": version,
        "main_file_name": main_file_name,
        "status": "UPLOADED",
        "comment": comment,
        "zip_file_path": engine_zip_path,
        "timestamp": datetime.now().isoformat()
    }

    save_tracker(engines_tracker)

    logger.info(f"Engine '{tag}' uploaded successfully")
    return {"status": "ok", "msg": f"Engine '{tag}' uploaded successfully"}

async def list_engines():
    return engines_tracker

async def compile_engine(tag: str = Form(...)):
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

    engine_info = engines_tracker[tag]
    version = engine_info["version"]
    main_file_name = engine_info["main_file_name"]

    if engine_info.get("status") == "COMPILED":
        return {"message": f"Engine '{tag}' already compiled", "status": "SKIPPED"}

    # --- Prepare build dir ---
    build_path = os.path.join(BUILD_DIR_PATH, f"{tag}_{version}")
    # os.makedirs(build_path, exist_ok=True)

    # --- Unzip engine ---
    zip_path = os.path.join(ENGINES_DIR_PATH, f"{tag}_{version}.zip")
    if not os.path.exists(zip_path):
        return {"error": f"Engine zip file not found: {zip_path}"}

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(build_path)

    # --- Rename main P4 file ---
    src_main_path = os.path.join(build_path, main_file_name)
    dst_main_path = os.path.join(build_path, f"{tag}_{version}.p4")

    if not os.path.exists(src_main_path):
        return {"error": f"Main P4 file '{main_file_name}' not found in zip"}

    shutil.move(src_main_path, dst_main_path)

    # --- Compile ---
    log_path = os.path.join(build_path, "compile.log")
    program_name = f"{tag}_{version}"

    cmd = [
        "time",
        os.path.join(TOOLS_DIR_PATH, "p4_build.sh"),
        "-p", dst_main_path
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
            engines_tracker[tag]["status"] = "COMPILED"
            with open(TRACKER_FILE_PATH, "w") as f:
                json.dump(engines_tracker, f, indent=2)
            return {"message": f"Engine '{tag}' compiled successfully", "status": "COMPILED"}
        else:
            engines_tracker[tag]["status"] = "COMPILE_ERROR"
            with open(TRACKER_FILE_PATH, "w") as f:
                json.dump(engines_tracker, f, indent=2)

            with open(log_path, 'r') as f:
                log_content = f.read()
            return {
                "error": f"Compilation failed for engine '{tag}'",
                "status": "COMPILE_ERROR",
                "log_path": log_path,
                "log": log_content,
            }
    except Exception as e:
        return {"error": str(e), "status": "COMPILE_EXCEPTION"}

