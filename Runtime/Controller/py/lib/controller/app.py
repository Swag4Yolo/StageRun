import os
import shutil
import logging
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException, File
from pathlib import Path
import traceback

# Import StageRun libs
import lib.controller.state_manager as sm
from lib.utils.status import *
from lib.utils.manifest_parser import *
from lib.utils.utils import *
from lib.tofino.tofino_controller import *

logger = logging.getLogger("controller")

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

    if app_key in sm.apps:
        logger.warning(f"Upload rejected: app '{app_key}' with version v{version} already exists")
        return {"status": "error", "msg": f"App '{app_key}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"App '{tag}' with version v{version} already exists")
    

    app_dir_path = os.path.join(sm.APPS_DIR_PATH, f"{app_key}/")
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
    
    manifest_path = os.path.join(sm.APPS_DIR_PATH, f"{app_key}/manifest.yaml")

    with open(manifest_path, "wb") as f:
        shutil.copyfileobj(manifest_file.file, f)

    sm.apps[app_key] = {
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

    sm.save_apps()

    logger.info(f"App '{app_key}' uploaded successfully")

    return {"status": "ok", "msg": f"App '{app_key}' uploaded successfully"}

async def list_apps():
    if len(sm.apps) == 0:
        raise HTTPException(404, "No apps have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    for _, info in sm.apps.items():
        tag = info["tag"]
        version = info["version"]
        status = info.get("status", STATUS_UNKNOWN)
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}

    return grouped

async def remove_app(tag: str, version: str):

    app_key = f"{tag}_v{version}"

    if app_key not in sm.apps:
        return {"status": "error", "message": f"Engine {app_key} not found."}

    if sm.apps[app_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed app."}
    
    if sm.apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": "Cannot remove a running app."}

    # Delete files

    # Path(sm.apps[app_key]["app_path"]).unlink(missing_ok=True)
    shutil.rmtree(sm.apps[app_key]["app_dir_path"], ignore_errors=True)

    # Remove from tracker
    sm.apps.pop(app_key, None)
    sm.save_apps()

    return {"status": "ok", "message": f"App {app_key} removed."}

# def check_port_compatibility(base_ports: dict, new_ports: dict):
#     """
#     Compare new_ports with base_ports (a category).
#     Returns:
#       - "compatible" if identical
#       - "extend" if compatible but new ports need to be added
#       - "incompatible" if specs clash
#     """
#     extended = False
    
#     print("check_ports compatibility")
#     print(base_ports)
#     print(new_ports)

#     for port, new_spec in new_ports.items():
#         if port not in base_ports:
#             extended = True  # new port, no clash
#         else:
#             base_spec = base_ports[port]
#             if base_spec != new_spec:
#                 return "incompatible"  # mismatch in spec
    
#     return "extend" if extended else "compatible"

def assign_program_to_category(app_key: str, new_ports: dict):

    for cat_name, cat_data in sm.port_sets.items():
        status = sm.check_port_compatibility(cat_data["ports"], new_ports)
        if status == "compatible":
            cat_data["programs"].append(app_key)
            return cat_name, "compatible"
        elif status == "extend":
            cat_data["ports"].update(new_ports)
            cat_data["programs"].append(app_key)
            return cat_name, "extended"

    # no match, create new category
    new_cat = f"category{len(sm.port_sets) + 1}"
    sm.port_sets[new_cat] = {
        "ports": new_ports,
        "programs": [app_key]
    }
    return new_cat, "new"


def validate_app(app_path, manifest, app_key, engine_key, program_id, target_hw=True):

    try:
        endpoints = get_endpoints(manifest) #EndpointsInfo

        # Program path is the compiled program
        # Program Name is the class name 
        SystemApp = load_stagerun_program(app_path)

        sm.connect_tofino()
        # for switch in switches:
        sys_app = SystemApp(sm.tofino_controller.runtime)

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
    if app_key not in sm.apps:
        return {"status": "error", "message": f"App {app_key} not found."}

    if sm.apps[app_key]["status"] == STATUS_INSTALLED:
        return {"status": "error", "message": f"App {app_key} already installed."}
    
    if sm.apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is already installed and running."}

    if sm.apps[app_key]["status"] == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if sm.apps[app_key]["status"] == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}

    app_file_path = sm.apps[app_key]["app_path"]
    manifest_file_path = sm.apps[app_key]["manifest_path"]
   
    manifest = parse_manifest(manifest_file_path)
    if not 'switch' in manifest or not 'ports' in manifest['switch']:
        sm.apps[app_key]['status'] = STATUS_BAD_MANIFEST
        sm.save_apps()
        return {"status": "error", "message": f"Bad Manifest File. Missing 'switch' or 'ports' in switch"}
    

    engine_key = sm.running_engine[sm.RUNNING_ENGINE]['engine_key']
    
    if engine_key not in sm.engines:
        return {"status": "error", "message": f"Please install an engine before installing an app"}

    program_id = sm.allocate_pid()
    valid_app, message = validate_app(app_file_path, manifest, app_key, engine_key, program_id, True)
    if not valid_app:
        sm.apps[app_key]['status'] = STATUS_BAD_APP
        sm.remove_program_id(app_key)
        sm.save_apps()
        return {"status": "error", "message": f"App {app_key} is not valid. {message}"}
    
    sm.set_pid(program_id, app_key)
    sm.apps[app_key]['status'] = STATUS_INSTALLED
    sm.save_apps()

    # print(app_key)
    # print(manifest['switch']['ports'])
    # [{'49/-': {'speed': 100, 'loopback': False}}, {'50/-': {'speed': 100, 'loopback': False}}]
    assign_program_to_category(app_key, manifest['switch']['ports'])
    sm.save_port_sets()

    return {"status": "ok", "message": f"App {app_key} Installed successfully."}

    # TODO: assuming a unique StageRunEngine format for now
    # The Controller knows how to install all the instructions in all stages. It needs to know which instructions are available in each stage. If needs to know which instructions that runtime has and which instructions are available in each stage.

async def run_app(tag: str, version: str):
    # [X] 1. If is 1st app to run then pre rules need to be installed
    # [] 1.1 Install Ports
    # [] 2. If not:
    # []    2.1 Check Ports category is different from the one we have know:
    # []          2.1.1 Change ports
    # []      2.2 Check Port

    app_key = f"{tag}_v{version}"

    if app_key not in sm.apps:
        return {"status": "error", "message": f"Engine {app_key} not found."}
    
    if sm.apps[app_key]["status"] == STATUS_UPLOADED:
        return {"status": "error", "message": f"App {app_key} was uploaded and not installed."}

    if sm.apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is running. A running app cannot be uninstalled. Please change the running app."}

    if sm.apps[app_key]["status"] == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if sm.apps[app_key]["status"] == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}
    
    if sm.apps[app_key]["status"] == STATUS_INSTALLED:
        sm.run_program(app_key)
        sm.apps[app_key]['status'] = STATUS_RUNNING
        for key in sm.apps:
            # Previous Running App is changed to STATUS_INSTALLED
            if key != app_key and sm.apps[key]['status'] == STATUS_RUNNING:
                sm.apps[key]['status']=STATUS_INSTALLED
        sm.save_apps()

        return {"status": "ok", "message": f"App {app_key} running"}

    else:
        return {"status": "error", "message": f"App {app_key} does not follow one of the internal status, so uninstalling is not possible."}
    

async def uninstall_app(tag: str, version: str):
    # 0. If the app is running, cannot uninstall
    # 1. free program_id
    # 2. Delete all table entries with that program_id
    app_key = f"{tag}_v{version}"

    if app_key not in sm.apps:
        return {"status": "error", "message": f"Engine {app_key} not found."}

    if sm.apps[app_key]["status"] == STATUS_UPLOADED:
        return {"status": "error", "message": f"App {app_key} was uploaded and not installed."}

    if sm.apps[app_key]["status"] == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is running. A running app cannot be uninstalled. Please change the running app."}

    if sm.apps[app_key]["status"] == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if sm.apps[app_key]["status"] == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}
    
    if sm.apps[app_key]["status"] == STATUS_INSTALLED:
        sm.remove_program_id(app_key)

        return {"status": "ok", "message": f"App {app_key} has been uninstalled successfully."}

    else:
        return {"status": "error", "message": f"App {app_key} does not follow one of the internal status, so uninstalling is not possible."}
    