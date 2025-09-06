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
import traceback
import re

# Import StageRun libs
from engine import load_engines, load_running_engine, RUNNING_ENGINE, get_program_id, remove_program_id, set_program_id
from lib.utils.status import *
from lib.utils.manifest_parser import *
from lib.utils.utils import *
from lib.tofino.tofino_controller import *

logger = logging.getLogger("controller")

# App Status = {Uploaded, Installed, Running}

# Managing Apps
APPS_DIR_PATH = None
APPS_FILE_PATH = None
APP_RUNNING_FILE_PATH = None
PORT_SETS = None
apps = {}
running_app = {}
port_sets = {}
tofino_controller = None

# -----------------------
# Initialization
# -----------------------
def init_app(config):
    """Initialize app module with config paths."""
    global \
    APPS_DIR_PATH, APPS_FILE_PATH, APP_RUNNING_FILE_PATH, APP_RUNNING_FILE_PATH, apps, running_app, PORT_SETS, port_sets

    STAGE_RUN_ROOT_PATH = config["stagerun_root"]

    APPS_DIR_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["apps_dir"])
    APPS_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["tracker_file"])
    APP_RUNNING_FILE_PATH = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["running_app"])
    PORT_SETS = os.path.join(STAGE_RUN_ROOT_PATH, config["apps"]["port_set"])

    # Apps
    os.makedirs(APPS_DIR_PATH, exist_ok=True)
    apps = load_apps()
    running_app = load_running_app()
    logger.info(f"App system initialized with dir={APPS_DIR_PATH}, tracker={APPS_FILE_PATH}")
    port_sets = load_port_sets()
        
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

# Ports
def load_port_sets():
    if PORT_SETS and os.path.exists(PORT_SETS):
        try:
            with open(PORT_SETS, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Running App file corrupted, resetting...")
            return {}
    return {}

def save_port_sets(port_sets):
    with open(PORT_SETS, "w+") as f:
        json.dump(port_sets, f, indent=2)


def connect_tofino():
    global tofino_controller
    _running_engine = load_running_engine()
    engine_key = _running_engine[RUNNING_ENGINE]['engine_key']
    _engines = load_engines()
    if engine_key != "" and engine_key in _engines:
        if tofino_controller == None or tofino_controller.engine_key != engine_key:
            tofino_controller = TofinoController(engine_key)

async def upload_app(
    app_file: UploadFile = File(...),
    manifest_file: UploadFile = File(...),
    tag: str = Form(...),
    version: str = Form(...),
    comment: str = Form("")
):
    """
        This function is responsible for receiving an application with a manifest file for configuring the switch.
        - The app file format is .py
        - The manifest file format is .yaml
    """
    app_key = f"{tag}_v{version}"

    logger.info(f"Received upload request for App '{app_key}'")

    if app_key in apps:
        logger.warning(f"Upload rejected: app '{app_key}' with version v{version} already exists")
        return {"status": "error", "msg": f"App '{app_key}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"App '{tag}' with version v{version} already exists")
    

    app_dir_path = os.path.join(APPS_DIR_PATH, f"{app_key}/")
    os.makedirs(app_dir_path, exist_ok=True)

    ####### Processing App File
    _, ext = os.path.splitext(app_file.filename)
    if not ext or ext != '.py': 
        return {"status": "error", "msg": f"The provided {app_file.filename} does not have a supported extension"}
    
    app_path = os.path.join(app_dir_path, f"app.py")

    with open(app_path, "wb") as f:
        shutil.copyfileobj(app_file.file, f)

    ####### Processing Manifest File
    _, ext = os.path.splitext(manifest_file.filename)
    if not ext or ext != '.yaml':
        return {"status": "error", "msg": f"The provided {manifest_file.filename} does not have a supported extension"}
    
    manifest_path = os.path.join(APPS_DIR_PATH, f"{app_key}/manifest.yaml")

    with open(manifest_path, "wb") as f:
        shutil.copyfileobj(manifest_file.file, f)

    apps[app_key] = {
        "tag": tag,
        "version": version,
        "status": "UPLOADED",
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
        "app_dir_path": app_dir_path,
        "app_path": app_path,
        "manifest_path": manifest_path,
        "port_set": "",
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
        status = info.get("status", STATUS_UNKNOWN)
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}

    return grouped

async def remove_app(tag: str, version: str):

    app_key = f"{tag}_v{version}"
    if app_key not in apps:
        return {"status": "error", "message": f"Engine {app_key} not found."}

    if apps[app_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed app."}
    
    if apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": "Cannot remove a running app."}

    # Delete files

    # Path(apps[app_key]["app_path"]).unlink(missing_ok=True)
    shutil.rmtree(apps[app_key]["app_dir_path"], ignore_errors=True)

    # Remove from tracker
    apps.pop(app_key, None)
    save_apps(apps)

    return {"status": "ok", "message": f"App {app_key} removed."}

def check_port_compatibility(base_ports: dict, new_ports: dict):
    """
    Compare new_ports with base_ports (a category).
    Returns:
      - "compatible" if identical
      - "extend" if compatible but new ports need to be added
      - "incompatible" if specs clash
    """
    extended = False
    
    print("check_ports compatibility")
    print(base_ports)
    print(new_ports)

    for port, new_spec in new_ports.items():
        if port not in base_ports:
            extended = True  # new port, no clash
        else:
            base_spec = base_ports[port]
            if base_spec != new_spec:
                return "incompatible"  # mismatch in spec
    
    return "extend" if extended else "compatible"

def assign_program_to_category(app_key: str, new_ports: dict):

    for cat_name, cat_data in port_sets.items():
        status = check_port_compatibility(cat_data["ports"], new_ports)
        if status == "compatible":
            cat_data["programs"].append(app_key)
            return cat_name, "compatible"
        elif status == "extend":
            cat_data["ports"].update(new_ports)
            cat_data["programs"].append(app_key)
            return cat_name, "extended"

    # no match, create new category
    new_cat = f"category{len(port_sets) + 1}"
    port_sets[new_cat] = {
        "ports": new_ports,
        "programs": [app_key]
    }
    return new_cat, "new"


def validate_app(app_path, manifest, app_key, engine_key, program_id, target_hw=True):
    global tofino_controller

    try:
        endpoints = get_endpoints(manifest) #EndpointsInfo

        # Program path is the compiled program
        # Program Name is the class name 
        SystemApp = load_stagerun_program(app_path)

        connect_tofino()
        # for switch in switches:
        sys_app = SystemApp(tofino_controller.runtime)

        # Map endpoint name to port
        name_to_port = {e.name: e.port for e in endpoints}

        # Get install method parameters
        param_names = list(inspect.signature(sys_app.install).parameters)

        # Check if all required names exist in endpoints (except possibly the last one if it's target_hw)
        if len(param_names) < 2:
            return False, "The application does not have the necessary arguments in the SystemApp method. Missing one of the target_hw or program_id arguments."
        if not param_names[-2] == 'target_hw' or not param_names[-1] == 'program_id':
            return False, "The application does not have the necessary arguments in the SystemApp method. Missing one of the target_hw or program_id arguments."

        expected_endpoint_names = param_names[:-2] 

        # Ensure we have all required endpoint ports
        if all(name in name_to_port for name in expected_endpoint_names):
            # Build the argument list
            args = [name_to_port[name] for name in expected_endpoint_names]

            # If 'target_hw' is expected, add it
            if param_names and param_names[-2] == 'target_hw' and param_names[-1] == 'program_id':
                args.append(target_hw)
                args.append(program_id)

                sys_app.install(*args)
                return True, ""
        else:
            missing = [name for name in expected_endpoint_names if name not in name_to_port]
            return False, f"Missing endpoint(s) for: {missing}"
        
    except Exception as e:
        logger.error(traceback.format_exc())
        return False, f"Failed to Install the Application. {repr(e)}"

async def install_app(tag: str, version: str):

    app_key = f"{tag}_v{version}"
    if app_key not in apps:
        return {"status": "error", "message": f"App {app_key} not found."}

    if apps[app_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": f"App {app_key} already installed."}
    
    if apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is already installed and running."}

    if apps[app_key]["status"] == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if apps[app_key]["status"] == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}

    app_file_path = apps[app_key]["app_path"]
    manifest_file_path = apps[app_key]["manifest_path"]
   
    manifest = parse_manifest(manifest_file_path)
    if not 'switch' in manifest or not 'ports' in manifest['switch']:
        apps[app_key]['status'] = STATUS_BAD_MANIFEST
        save_apps(apps)
        return {"status": "error", "message": f"Bad Manifest File. Missing 'switch' or 'ports' in switch"}
    

    _engines = load_engines()
    _running_engine = load_running_engine()
    engine_key = _running_engine[RUNNING_ENGINE]['engine_key']
    
    if engine_key not in _engines:
        return {"status": "error", "message": f"Please Initialize a Running Engine First"}

    program_id = get_program_id()
    print("program_id", program_id)
    valid_app, message = validate_app(app_file_path, manifest, app_key, engine_key, program_id, True)
    if not valid_app:
        apps[app_key]['status'] = STATUS_BAD_APP
        remove_program_id(program_id)
        save_apps(apps)
        return {"status": "error", "message": f"App {app_key} is not valid. {message}"}
    
    set_program_id(program_id, app_key)
    apps[app_key]['status'] = STATUS_INSTALLED
    save_apps(apps)

    print(app_key)
    print(manifest['switch']['ports'])
    # [{'49/-': {'speed': 100, 'loopback': False}}, {'50/-': {'speed': 100, 'loopback': False}}]
    assign_program_to_category(app_key, manifest['switch']['ports'])
    save_port_sets(port_sets)

    return {"status": "ok", "message": f"App {app_key} Installed succesfully."}

    # TODO: assuming a unique StageRunEngine format for now
    # The Controller knows how to install all the instructions in all stages. It needs to know which instructions are available in each stage. If needs to know which instructions that runtime has and which instructions are available in each stage.

def clear_apps_engine_uninstall():
    for app_key in apps:
        if apps[app_key]['status'] in [STATUS_INSTALLED, STATUS_RUNNING]:
            apps[app_key]['status'] = STATUS_UPLOADED
    
    save_apps(apps)

async def run_app(tag: str, version: str):
    global tofino_controller
    # [] 1. If is 1st app to run then pre rules need to be installed
    # [] 1.1 Install Ports
    # [] 2. If not:
    # []    2.1 Check Ports category is different from the one we have know:
    # []          2.1.1 Change ports
    # []      2.2 Check Port
    connect_tofino()

    app_key = f"{tag}_v{version}"
    port_set = None

    #port_key == port category
    for port_key in port_sets:
        if app_key in port_sets[port_key]['programs']:
            port_set = port_sets[port_key]
            break
        """
            {
        "category1": {
            "ports": {
            "49/-": {
                "speed": 100,
                "loopback": false
            },
            "50/-": {
                "speed": 100,
                "loopback": false
            }
            },
            "programs": [
            "NetHide_v1_0"
            ]
        }

        }
        """
    # port_cfg {'49/-': {'speed': 100, 'loopback': False}}
    for front_port in port_set['ports']:
            match = re.search(r"(\d+)/", front_port)
            if match:
                p_num = match.group(1)
                print("p_num", p_num)
            else:
                #TODO: error
                print("ERROR")
                
            print("front_port", front_port)
            port = port_set['ports'][front_port]

            speed = PORT_SPEED_BF[port['speed']]
            loopback = PORT_LOOPBACK_BF[port['loopback']]
            fec = PORT_FEC_BF.get( (speed, loopback), FEC_NONE)

            print("Port configs:")
            print("p_num", p_num)
            print("speed", speed)
            print("loopback", loopback)
            print("fec", fec)

            tofino_controller.port_mechanism.add_port(front_port=int(p_num), speed=speed, loopback=loopback, fec=fec)

    # tc. program _id mechanism = program_id

    apps[app_key]['status'] = STATUS_RUNNING
    save_apps(apps)

    return {"status": "ok", "message": f"App {app_key} Running succesfully."}

async def uninstall_app(tag: str, version: str):
    # 0. If the app is running, cannot uninstall
    # 1. free program_id
    # 2. Delete all table entries with that program_id
    # 
    pass