import os
import logging
import json
from time import sleep
import re

from lib.controller.types import App, Engine
from lib.tofino.tofino_controller import TofinoController
from lib.tofino.constants import *
from lib.utils.status import *
from lib.engine.engine_controller import EngineController
# from lib.utils.manifest_parser import parse_manifest
from lib.utils.utils import parse_json, Timer

logger = logging.getLogger(__name__)
timer = Timer()
###########################################################
#                       Engine State                      #
###########################################################
# Engine Status = {Uploaded, Compiled, Installed}

RUNNING_ENGINE = "__running__engine__"
RUNNING_SESSION_NAME = "run_switchd"

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

# Compiler
p4_native_compiler_path = None
STAGE_RUN_ROOT_PATH = None
COMPILER_VERSION = None

def init_engine_state(config):
    """Initialize engine module with config paths."""
    global ENGINES_DIR_PATH, ENGINES_FILE_PATH, engines, BUILD_DIR_PATH, TOOLS_DIR_PATH, HW_FLAGS, p4_native_compiler_path, STAGE_RUN_ROOT_PATH, RUNNING_ENGINE_FILE_PATH, running_engine, COMPILER_VERSION #\
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
    COMPILER_VERSION = config["compiler"]["version"]


    # Engines
    os.makedirs(ENGINES_DIR_PATH, exist_ok=True)
    engines.update(load_engines())
    running_engine.update(load_running_engine())
    # print("Running Engine")
    # print(running_engine)
    logger.info(f"Engine system initialized with dir={ENGINES_DIR_PATH}, tracker={ENGINES_FILE_PATH}")

    # Compiler
    os.makedirs(BUILD_DIR_PATH, exist_ok=True)
    p4_native_compiler_path = f"{TOOLS_DIR_PATH}/p4_build.sh"
    if not os.path.isfile(p4_native_compiler_path):
        logger.error(f"Failed to Initialize Engine, native compiler not found in {TOOLS_DIR_PATH}.")
        exit(1)
        
def load_engines():
    if ENGINES_FILE_PATH and os.path.exists(ENGINES_FILE_PATH):
        try:
            with open(ENGINES_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Tracker file corrupted, resetting...")
            return {}
    return {}

def save_engines():
    global engines
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

def save_running_engine():
    global running_engine
    with open(RUNNING_ENGINE_FILE_PATH, "w+") as f:
        json.dump(running_engine, f, indent=2)

def get_engine_ISA(engine_key):
    global engines
    return parse_json(engines[engine_key]['isa_path'])

def get_engine_recirc_ports(engine_key):
    global engines
    return engines[engine_key]['recirc_ports']

def is_an_engine_running():
    global running_engine
    return running_engine[RUNNING_ENGINE]['engine_key'] != ""

def get_running_engine_key():
    global running_engine
    return running_engine[RUNNING_ENGINE]['engine_key']

def get_engine_key(tag:str, version:str):
    return f"{tag}_v{version}"

def exists_engine(engine_key):
    global engines
    return engine_key in engines

def add_engine(engine: Engine):
    global engines
    engines[engine.engine_key] = {
        "tag": engine.tag,
        "version": engine.version,
        "main_file_name": engine.main_file_name,
        "status": engine.status,
        "comment": engine.comment,
        "zip_path": engine.zip_path,
        "isa_path": engine.isa_path,
        "build_path": engine.build_path,
        "timestamp": engine.timestamp,
        "recirc_ports": engine.recirc_ports
    }
    save_engines()

def get_engine(engine_key) -> Engine:
    global engines
    return Engine.from_dict(engine_key, engines[engine_key])

def get_engines():
    global engines
    lst_engines = []
    for engine_key in engines:
        lst_engines.append(Engine.from_dict(engine_key, engines[engine_key]))

    return lst_engines

def update_engine(engine: Engine):
    engines[engine.engine_key] = {
        "tag": engine.tag,
        "version": engine.version,
        "main_file_name": engine.main_file_name,
        "status": engine.status,
        "comment": engine.comment,
        "zip_path": engine.zip_path,
        "isa_path": engine.isa_path,
        "build_path": engine.build_path,
        "timestamp": engine.timestamp,
        "recirc_ports": engine.recirc_ports
    }
    save_engines()

def set_engine_status(engine_key, status):
    global engines
    engines[engine_key]["status"] = status
    save_engines()

def set_running_engine(engine_key, log_path):
    global running_engine
    running_engine[RUNNING_ENGINE] = {
            "engine_key": engine_key,
            "log": log_path,
            "program_ids": {},
            "free_pids": [],
    }
    save_running_engine()

def reset_running_engine():
    global running_engine
    running_engine[RUNNING_ENGINE] = {
            "engine_key": "",
            "log": "",
            "program_ids": {},
            "free_pids": [],
    }
    save_running_engine()

def delete_engine(engine_key):
    global engines
    engines.pop(engine_key, None)
    save_engines()

###########################################################
#                         App State                       #
###########################################################
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
engine_controller = None

def init_app_state(config):
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
    apps.update(load_apps())
    running_app.update(load_running_app())
    logger.info(f"App system initialized with dir={APPS_DIR_PATH}, tracker={APPS_FILE_PATH}")
    port_sets = load_port_sets()

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

def save_port_sets():
    global port_sets
    with open(PORT_SETS, "w+") as f:
        json.dump(port_sets, f, indent=2)

        
def load_apps():
    if APPS_FILE_PATH and os.path.exists(APPS_FILE_PATH):
        try:
            with open(APPS_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Running App file corrupted, resetting...")
            return {}
    return {}

def save_apps():
    global apps
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

def save_running_app():
    global running_app
    with open(APP_RUNNING_FILE_PATH, "w+") as f:
        json.dump(running_app, f, indent=2)

def connect_tofino():
    print("[+] Tofino Connection Startup")
    global tofino_controller
    global engine_controller
    global running_engine
    global engines

    engine_key = running_engine[RUNNING_ENGINE]['engine_key']
    if engine_key != "" and engine_key in engines:
        if tofino_controller == None or tofino_controller.engine_key != engine_key:
            
            print("Initializing Tofino and Engine's Controller")
            print("Sleeping 5s")
            logger.info("Initializing Tofino and Engine's Controller")
            logger.info("Sleeping 5s")
            sleep(5)
            tofino_controller = TofinoController(engine_key)
            engine_controller = EngineController(tofino_controller.runtime)

    print("[✓] Tofino Connection")

def disconnect_tofino():
    global tofino_controller, engine_controller

    tofino_controller = None
    engine_controller = None

    ####### Program IDS Management #######

def get_program_id(app_key):
    for pid in running_engine[RUNNING_ENGINE]["program_ids"]:
        if app_key == running_engine[RUNNING_ENGINE]["program_ids"][pid]:
            return pid
    return None

def allocate_pid():
    global running_engine
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

def set_pid(pid, app_key):
    global running_engine
    running_engine[RUNNING_ENGINE]["program_ids"][str(pid)] = app_key
    save_running_engine()

def remove_program_id(app_key, *, force=False, program_id=None):
    """
        For removing a program:
        1. Update the internal state, freeing 
        2. Remove the program from the engine
    """
    global running_engine
    global engine_controller
    
    program = None
    pid = None
    
    # 1. Update Controllers Stage about apps
    for pid in running_engine[RUNNING_ENGINE]["program_ids"]:
        program = running_engine[RUNNING_ENGINE]["program_ids"][pid]
        if app_key == program:
            del running_engine[RUNNING_ENGINE]["program_ids"][pid]
            running_engine[RUNNING_ENGINE].setdefault("free_pids", []).append(pid)
            break
    for category in port_sets:
        if app_key in port_sets[category]["programs"]:
            port_sets[category]["programs"].remove(app_key)
            if len(port_sets[category]["programs"]) == 0:
                del port_sets[category]
                break
    save_port_sets()
    save_running_engine()
    apps[app_key]["status"]=STATUS_UPLOADED
    save_apps()
    if pid:
        # 2. Update Tables and configurations inside the Engine
        connect_tofino()
        engine_controller.remove_program(int(pid))

    elif force and program_id:
        logger.debug(f"[!] Forcefully removing app {app_key}")
        connect_tofino()
        engine_controller.remove_program(int(program_id))

    else:
        logger.info(f"Deleting App {app_key} unsuccessful since it is not installed in the Engine or not detected in the state")


def clear_program_ids():
    global running_engine
    running_engine[RUNNING_ENGINE]["program_ids"] = {}
    running_engine[RUNNING_ENGINE]["free_pids"] = []
    save_running_engine()

def clear_apps():
    for app_key in apps:
        if apps[app_key]['status'] in [STATUS_INSTALLED, STATUS_RUNNING]:
            apps[app_key]['status'] = STATUS_UPLOADED

    save_apps()

def clear_port_sets():
    global port_sets
    port_sets = {}
    save_port_sets()

def check_port_compatibility(base_ports: dict, new_ports: dict):
    """
    Compare new_ports with base_ports (a category).
    Returns:
      - "compatible" if identical
      - "extend" if compatible but new ports need to be added
      - "incompatible" if specs clash
    """
    extended = False
    
    # print("check_ports compatibility")
    # print(base_ports)
    # print(new_ports)

    for port, new_spec in new_ports.items():
        if port not in base_ports:
            extended = True  # new port, no clash
        else:
            base_spec = base_ports[port]
            if base_spec != new_spec:
                return "incompatible"  # mismatch in spec
    
    return "extend" if extended else "compatible"


def get_running_app():
    for key in apps:
        if apps[key]["status"] == STATUS_RUNNING:
            return key
    return None

def get_ports_cat(app_key):
    for category in port_sets:
        if app_key in port_sets[category]["programs"]:
            return category
    return None

def get_ports_list_from_category(category):
    ports = []
    for front_port in port_sets[category]['ports']:
            match = re.search(r"(\d+)/", front_port)
            if match:
                p_num = match.group(1)
                ports.append(int(p_num))
    return ports

def install_port_cat(category):
    # for category in port_sets:
    #     if app_key in port_sets[category]['programs']:
    #         port_set = port_sets[category]
    #         break
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
    for front_port in port_sets[category]['ports']:
            match = re.search(r"(\d+)/", front_port)
            if match:
                p_num = match.group(1)
                # print("p_num", p_num)
            else:
                #TODO: error
                print("ERROR")
                
            print("front_port", front_port)
            port = port_sets[category]['ports'][front_port]

            speed = PORT_SPEED_BF[port['speed']]
            loopback = PORT_LOOPBACK_BF[port['loopback']]
            fec = PORT_FEC_BF.get( (speed, loopback), FEC_NONE)

            # print("Port configs:")
            # print("p_num", p_num)
            # print("speed", speed)
            # print("loopback", loopback)
            # print("fec", fec)

            tofino_controller.port_mechanism.add_port(front_port=int(p_num), speed=speed, loopback=loopback, fec=fec)

def run_program(app_key):
    # Old running app
    prev_run_app_key = get_running_app()
    
    # New running app
    pid = get_program_id(app_key)
    new_cat = get_ports_cat(app_key)
    new_ports = get_ports_list_from_category(new_cat)

    if pid == None or new_cat == None or len(new_ports) == 0:
        print("ERROR; RETURNING")
        return

    if prev_run_app_key:
        running_app_category = get_ports_cat(prev_run_app_key)

    if prev_run_app_key == None:
        if __debug__:
            timer.start()
        install_port_cat(new_cat)
        if __debug__:
            timer.finish()
            timer.calc(f"Time for Installing Ports {app_key}")
        # Configure Engine (change pid to pid of new app, and put ports => pid)
        if __debug__:
            timer.start()
        engine_controller.run_program(app_key, pid, new_ports)
        if __debug__:
            timer.finish()
            timer.calc("Time for changing the Running Program")

    elif check_port_compatibility(port_sets[running_app_category]["ports"], port_sets[new_cat]["ports"]) == "compatible":
        engine_controller.run_program(app_key, pid, new_ports)
    else:
        logger.debug(f"Chaning Tofino Ports {app_key}")
        # old_cat = get_ports_cat(prev_run_app_key)
        # remove_ports(old_cat)
        if __debug__:
            timer.start()
        tofino_controller.port_mechanism.clear_ports()
        if __debug__:
            timer.finish()
            timer.calc(f"Time for Clearing Ports {app_key}")

        if __debug__:
            timer.start()
        install_port_cat(new_cat)
        if __debug__:
            timer.finish()
            timer.calc(f"Time for Installing Ports {app_key}")
        
        if __debug__:
            timer.start()
        engine_controller.run_program(app_key, pid, new_ports)
        if __debug__:
            timer.finish()
            timer.calc(f"Time for Changing the Running Program {app_key}")
        

    # Clearing the Registers
    # connect_tofino()
    # timer.start()
    # engine_controller.clear_state()
    # timer.finish()
    # timer.calc(f"Cleaned Registers for App {app_key}")

def get_app_key(tag, version):
    return f"{tag}_v{version}"

def add_app(app: App):
    global apps

    apps[app.app_key] = {
        "tag": app.tag,
        "version": app.version,
        "status": app.status,
        "comment": app.comment,
        "timestamp": app.timestamp,
        "app_dir_path": app.app_dir_path,
        "app_path": app.app_path,
        "manifest_path": app.manifest_path,
        "port_set": app.port_set,
    }
    save_apps()

def delete_app(app_key):
    global apps
    apps.pop(app_key, None)
    save_apps()

def exists_app(app_key):
    global apps
    return app_key in apps

def get_apps():
    global apps

    lst_apps = []
    for app_key in apps:
        lst_apps.append(App.from_dict(app_key, apps[app_key]))
    
    return lst_apps

def get_app(app_key) -> App:
    global apps
    return App.from_dict(app_key, apps[app_key])

def set_app_status(app_key, status):
    global apps
    apps[app_key]["status"] = status
    save_apps()

def set_running_app(app_key):
    global apps
    set_app_status(app_key, STATUS_RUNNING)
    for key in apps:
        # Previous Running App is changed to STATUS_INSTALLED
        if key != app_key and apps[key]['status'] == STATUS_RUNNING:
            apps[key]['status']=STATUS_INSTALLED
    save_apps()