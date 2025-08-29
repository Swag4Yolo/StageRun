import yaml
import uvicorn
import logging
from fastapi import FastAPI
from engine import *

# ------------------------
# Logging Setup
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("controller")

# ------------------------
# FastAPI Setup
# ------------------------
app = FastAPI()
app.post("/upload_engine")(upload_engine)
app.get("/list_engines")(list_engines)
app.post("/compile_engine")(compile_engine)

# ------------------------
# Main entry
# ------------------------
if __name__ == "__main__":
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Init engine with config paths
    init_engine(config)

    DEFAULT_IP = "127.0.0.1"
    DEFAULT_PORT = 1337
    host = config["server"].get("host", DEFAULT_IP)
    port = config["server"].get("port", DEFAULT_PORT)

    logger.info(f"Starting StageRun controller on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
