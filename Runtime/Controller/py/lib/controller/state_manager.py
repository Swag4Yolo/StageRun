import os
import logging
import json

from lib.tofino.tofino_controller import TofinoController
from lib.utils.status import *

logger = logging.getLogger("controller")

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

def init_engine_state(config):
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
    global tofino_controller
    global running_engine
    global engines

    engine_key = running_engine[RUNNING_ENGINE]['engine_key']
    if engine_key != "" and engine_key in engines:
        if tofino_controller == None or tofino_controller.engine_key != engine_key:
            tofino_controller = TofinoController(engine_key)


    ####### Program IDS Management #######
def get_program_id():
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

def set_program_id(pid, app_key):
    global running_engine
    running_engine[RUNNING_ENGINE]["program_ids"][str(pid)] = app_key
    save_running_engine()

def remove_program_id(pid):
    global running_engine
    pid_str = str(pid)
    if pid_str in running_engine[RUNNING_ENGINE]["program_ids"]:
        del running_engine[RUNNING_ENGINE]["program_ids"][pid_str]
        running_engine[RUNNING_ENGINE].setdefault("free_pids", []).append(pid)
    save_running_engine()


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
