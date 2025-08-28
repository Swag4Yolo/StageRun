import os
import shutil
import zipfile
import json
import logging
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException

class Engine():
    def __init__(self, tag="", version="v0.1", main_file_location=None, comment=""):
        self.tag = tag
        self.version = version
        self.main_file_location = main_file_location
        self.comment = comment

logger = logging.getLogger("controller")

# Globals set at init
ENGINES_DIR_PATH = None
TRACKER_FILE_PATH = None
engines_tracker = {}

# -----------------------
# Initialization
# -----------------------
def init_engine(config_paths: dict):
    """Initialize engine module with config paths."""
    global ENGINES_DIR_PATH, TRACKER_FILE_PATH, engines_tracker

    ENGINES_DIR_PATH = config_paths["engines_dir"]
    TRACKER_FILE_PATH = config_paths["tracker_file"]

    os.makedirs(ENGINES_DIR_PATH, exist_ok=True)
    engines_tracker = load_tracker()
    logger.info(f"Engine system initialized with dir={ENGINES_DIR_PATH}, tracker={TRACKER_FILE_PATH}")


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