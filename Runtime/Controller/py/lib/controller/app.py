import os
import shutil
import logging
from datetime import datetime
from fastapi import UploadFile, Form, HTTPException, File
from pathlib import Path
import traceback

# Import StageRun libs
from lib.controller.types import App
from lib.controller.constants import *
import lib.controller.state_manager as sm
from lib.utils.status import *
from lib.utils.manifest_parser import *
from lib.utils.utils import *
from lib.tofino.tofino_controller import *
from lib.controller.deployer.deployer import deploy_program
from Core.stagerun_isa import ISA

from Core.ast_nodes import ProgramNode
from Core.stagerun_graph.importer import load_stage_run_graphs

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
        - The app file format is .out
        - The manifest file format is .yaml
    """
    logger.debug(f"upload_app {tag} v{version}")

    app_key = sm.get_app_key(tag, version)

    logger.info(f"Received upload request for App '{app_key}'")

    if sm.exists_app(app_key):
        logger.warning(f"Upload rejected: app '{app_key}' with version v{version} already exists")
        return {"status": "error", "msg": f"App '{app_key}' with version v{version} already exists"}
        # raise HTTPException(status_code=400, detail=f"App '{tag}' with version v{version} already exists")
    

    app_dir_path = os.path.join(sm.APPS_DIR_PATH, f"{app_key}/")
    os.makedirs(app_dir_path, exist_ok=True)
 
    ####### Processing App File
    _, ext = os.path.splitext(app_file.filename)
    if not ext or ext != '.out': 
        return {"status": "error", "msg": f"The provided {app_file.filename} does not have a supported extension"}
    
    app_path = os.path.join(app_dir_path, f"app.out")

    with open(app_path, "wb") as f:
        shutil.copyfileobj(app_file.file, f)

    ####### Processing Manifest File
    _, ext = os.path.splitext(manifest_file.filename)
    if not ext or ext != '.yaml':
        return {"status": "error", "msg": f"The provided {manifest_file.filename} does not have a supported extension"}
    
    manifest_path = os.path.join(sm.APPS_DIR_PATH, f"{app_key}/manifest.yaml")

    with open(manifest_path, "wb") as f:
        shutil.copyfileobj(manifest_file.file, f)

    sm.add_app(
        App(
            app_key=app_key,
            tag=tag,
            version=version,
            status=STATUS_UPLOADED,
            comment=comment,
            timestamp=datetime.now().isoformat(),
            app_dir_path=app_dir_path,
            app_path=app_path,
            manifest_path=manifest_path,
            port_set=""
            )
        )

    sm.save_apps()

    logger.info(f"App '{app_key}' uploaded successfully")

    return {"status": "ok", "msg": f"App '{app_key}' uploaded successfully"}

async def list_apps():
    logger.debug(f"list_apps")

    if len(sm.apps) == 0:
        raise HTTPException(404, "No apps have been uploaded to the controller.")

    # Build dict grouped by tag → version → status
    grouped = {}
    for app in sm.get_apps():
        tag = app.tag
        version = app.version
        status = app.status
        if tag not in grouped:
            grouped[tag] = {}
        grouped[tag][version] = {"status": status}
    return grouped

async def remove_app(tag: str, version: str):
    
    logger.debug(f"remove_app {tag} v{version}")

    app_key = sm.get_app_key(tag, version)

    if not sm.exists_app(app_key):
        return {"status": "error", "message": f"Engine {app_key} not found."}

    app = sm.get_app(app_key)

    if app.status == STATUS_INSTALLED:
        return {"status": "error", "message": "Cannot remove an installed app."}
    
    if app.status == STATUS_RUNNING:
        return {"status": "error", "message": "Cannot remove a running app."}

    # Delete files

    # Path(sm.apps[app_key]["app_path"]).unlink(missing_ok=True)
    shutil.rmtree(sm.apps[app_key]["app_dir_path"], ignore_errors=True)

    # Remove from tracker
    sm.delete_app(app_key)

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


def validate_compiled_app(compiled_app_file_path, manifest_file_path, app_key, engine_key):
    try:

        compiled_app = load_stage_run_graphs(compiled_app_file_path)
        manifest = parse_manifest(manifest_file_path)

        # 0. controller.config.compiler_version == app.compiler_version
        isa_version = compiled_app["isa_version"]

        if isa_version != ISA.VERSION.value:
            return False, f"Application ISA Version {isa_version} not supported for by current controller with ISA {ISA.VERSION.value}"

        # 1. ISA must be known by controller
        # 1. engine ISA must support instr
        isa_list = ISA.get_ISA_values()
        engine_isa = sm.get_engine_ISA(engine_key)
        # TODO: do POSFILTERS
        for graph in compiled_app['graphs']:
            for instr in graph['nodes']:
                opcode = instr["op"]
                if opcode not in isa_list:
                    return False, f"Instruction {opcode} is not supported by the controller.", None, None

                if opcode not in engine_isa['ISA']:
                    return False, f"Instruction {opcode} is not supported by the running engine.", None, None

        # 2. Validate Manifest structure
        if not 'switch' in manifest or not 'ports' in manifest['switch']:
            sm.set_app_status(app_key, STATUS_BAD_MANIFEST)
            return False, {"status": "error", "message": f"Bad Manifest File. Missing 'switch' or 'ports' in switch"}, None, None

        endpoints = manifest['program']['Endpoints']
        ports = compiled_app['resources']['ingress_ports']
        ports.extend(compiled_app['resources']['egress_ports'])
        for port_name in ports:
            # 2.1 Validate Manifest has the necessary ports names for the apps
            if port_name not in endpoints:
                sm.set_app_status(app_key, STATUS_BAD_MANIFEST)
                return False, f"Port '{port_name}' not presented in the manifest file of the application", None, None
            # 2.2 Validate that all endpoints are in the setup
            if endpoints[port_name]['port'] not in manifest['switch']['ports']:
                sm.set_app_status(app_key, STATUS_BAD_MANIFEST)
                return False, f"Manifest Error: All Endpoints must be specified in the setup", None, None
            
        # 3. engine recirc ports must be compatible with the current testbed
        if sm.check_port_compatibility(manifest['switch']['ports'], sm.get_engine_recirc_ports(engine_key)) not in ['extend', 'compatible']:
            return False, "Ports are incompatible with existing engine", None, None

        return True, "", compiled_app, manifest
    
    except Exception as e:
        print(traceback.format_exc())
        return False, f"Failed to Validate the Compiled Application. {repr(e)}", None, None



async def install_app(tag: str, version: str):

    logger.debug(f"Installing app {tag} v{version}")

    app_key = sm.get_app_key(tag, version)

    if not sm.is_an_engine_running():
        return {"status": "error", "message": f"Please install an engine before installing an app"}

    engine_key = sm.get_running_engine_key()

    if not sm.exists_app(app_key):
        return {"status": "error", "message": f"App {app_key} not found."}

    app = sm.get_app(app_key)

    if app.status == STATUS_INSTALLED:
        return {"status": "error", "message": f"App {app_key} already installed."}
    
    if app.status == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is already installed and running."}

    if app.status == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if app.status == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}

    # app_file_path = sm.apps[app_key]["app_path"]
    compiled_app_file_path = app.app_path
    manifest_file_path = app.manifest_path
   


    valid_app, msg, compiled_app, manifest = validate_compiled_app(compiled_app_file_path, manifest_file_path, app_key, engine_key)

    if not valid_app:
        return {"status": "error", "message": msg}

    program_id = sm.allocate_pid()

    isInstalled, message = deploy_program(compiled_app, manifest, app_key, engine_key, program_id)

    #
    #  TODO: test the set_app_status not working
    if not isInstalled:
        sm.set_app_status(app_key, STATUS_UNSUPPORTED)
        # sm.apps[app_key]['status'] = STATUS_UNSUPPORTED
        sm.remove_program_id(app_key, force=True, program_id=program_id)
        # sm.save_apps()
        return {"status": "error", "message": f"App {app_key} is not supported. {message}"}

    sm.set_pid(program_id, app_key)
    sm.set_app_status(app_key, STATUS_INSTALLED)

    # Update App ports with the Engine recirc ports
    ports = manifest['switch']['ports']
    recirc_ports = sm.get_engine_recirc_ports(engine_key)
    for r_port in recirc_ports:
        pnum = recirc_ports[r_port]
        ports[pnum] = {
            "speed": 100,
            "loopback": True
        }
    assign_program_to_category(app_key, ports)
    sm.save_port_sets()

    sm.connect_tofino()
    sm.engine_controller._final_configs_(program_id)

    return {"status": "ok", "message": f"App {app_key} Installed successfully."}

    # TODO: assuming a unique StageRunEngine format for now
    # The Controller knows how to install all the instructions in all stages. It needs to know which instructions are available in each stage. If needs to know which instructions that runtime has and which instructions are available in each stage.


async def run_app(tag: str, version: str):

    logger.debug(f"run_app {tag} v{version}")
    # [X] 1. If is 1st app to run then pre rules need to be installed
    # [] 1.1 Install Ports
    # [] 2. If not:
    # []    2.1 Check Ports category is different from the one we have know:
    # []          2.1.1 Change ports
    # []      2.2 Check Port

    app_key = sm.get_app_key(tag, version)

    if not sm.is_an_engine_running():
        return {"status": "error", "message": f"Please install an engine before installing an app"}

    if not sm.exists_app(app_key):
        return {"status": "error", "message": f"App {app_key} not found."}
    
    app = sm.get_app(app_key)

    if app.status == STATUS_UPLOADED:
        return {"status": "error", "message": f"App {app_key} was uploaded and not installed."}

    if app.status == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is running. A running app cannot be uninstalled. Please change the running app."}

    if app.status == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if app.status == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}
    
    if app.status == STATUS_INSTALLED:
        sm.run_program(app_key)
        sm.set_running_app(app_key)
        return {"status": "ok", "message": f"App {app_key} running"}

    else:
        return {"status": "error", "message": f"App {app_key} does not follow one of the internal status, so uninstalling is not possible."}
    

async def uninstall_app(tag: str, version: str):

    logger.debug(f"uninstall_app {tag} v{version}")
    # 0. If the app is running, cannot uninstall
    # 1. free program_id
    # 2. Delete all table entries with that program_id
    app_key = sm.get_app_key(tag, version)

    if not sm.exists_app(app_key):
        return {"status": "error", "message": f"Engine {app_key} not found."}

    app = sm.get_app(app_key)

    if app.status == STATUS_UPLOADED:
        return {"status": "error", "message": f"App {app_key} was uploaded and not installed."}

    if app.status == STATUS_RUNNING:
        return {"status": "error", "message": f"App {app_key} is running. A running app cannot be uninstalled. Please change the running app."}

    if app.status == STATUS_BAD_MANIFEST:
        return {"status": "error", "message": f"App {app_key} has a bad manifest format. You need to remove, re-upload, and install again with the correct format."}
    
    if app.status == STATUS_BAD_APP:
        return {"status": "error", "message": f"App {app_key} has a bad app format. You need to remove, re-upload, and install again with the correct format."}
    
    if app.status == STATUS_INSTALLED:
        sm.remove_program_id(app_key)

        return {"status": "ok", "message": f"App {app_key} has been uninstalled successfully."}

    else:
        return {"status": "error", "message": f"App {app_key} does not follow one of the internal status, so uninstalling is not possible."}
    