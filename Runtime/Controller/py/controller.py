import yaml
import uvicorn
import logging
from fastapi import FastAPI
from lib.controller.engine import *
from lib.controller.app import *

# ------------------------
# Logging Setup
# ------------------------
# class StreamToLogger:
#     """
#     Fake file-like stream object that redirects writes to a logger instance.
#     """
#     def __init__(self, logger, log_level=logging.INFO):
#         self.logger = logger
#         self.log_level = log_level
#         self.linebuf = ''

#     def write(self, buf):
#         for line in buf.rstrip().splitlines():
#             self.logger.log(self.log_level, line.rstrip())

#     def flush(self):
#         pass  # Nothing needed here


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="controller.log",
    filemode="a" #w para sobrescrever
)
logging.root.setLevel(logging.DEBUG)
logger = logging.getLogger("controller")

# # Redirect stdout and stderr
# sys.stdout = StreamToLogger(logger, logging.INFO)
# sys.stderr = StreamToLogger(logger, logging.ERROR)

# ------------------------
# FastAPI Setup
# ------------------------
app = FastAPI()

# Engines
app.post("/upload_engine")(upload_engine)
app.get("/list_engines")(list_engines)
app.post("/compile_engine")(compile_engine)
app.post("/install_engine")(install_engine)
app.post("/uninstall_engine")(uninstall_engine)
app.delete("/remove_engine")(remove_engine)

# Apps
app.post("/upload_app")(upload_app)
app.get("/list_apps")(list_apps)
app.get("/install_app")(install_app)
app.get("/run_app")(run_app)
app.get("/uninstall_app")(uninstall_app)
# app.post("/compile_engine")(compile_engine)
app.delete("/remove_app")(remove_app)

# ------------------------
# Main entry
# ------------------------
if __name__ == "__main__":
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Init engine with config paths
    sm.init_engine_state(config)
    sm.init_app_state(config)

    DEFAULT_IP = "127.0.0.1"
    DEFAULT_PORT = 1337
    host = config["server"].get("host", DEFAULT_IP)
    port = config["server"].get("port", DEFAULT_PORT)

    logger.info(f"Starting StageRun controller on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
