from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import yaml
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("StageRunServer")

app = FastAPI()

class EngineRequest(BaseModel):
    engine_name: str

class Response(BaseModel):
    status: str
    msg: str

@app.post("/install_engine", response_model=Response)
def install_engine(req: EngineRequest):
    # 👇 Log engine name
    logger.info(f"Received install request for engine: {req.engine_name}")

    if req.engine_name == "bad_engine":
        return Response(status="error", msg="Installation failed")
    return Response(status="ok", msg=f"Engine {req.engine_name} installed")

@app.post("/compile_engine", response_model=Response)
def compile_engine(req: EngineRequest):
    # 👇 Log engine name
    logger.info(f"Received compile request for engine: {req.engine_name}")

    if req.engine_name == "broken_engine":
        return Response(status="error", msg="Compilation failed")
    return Response(status="ok", msg=f"Engine {req.engine_name} compiled")

if __name__ == "__main__":
    # Load YAML config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    DEFAULT_IP = "127.0.0.1"
    DEFAULT_PORT = 1337

    host = config["server"].get("host", DEFAULT_IP)
    port = config["server"].get("port", DEFAULT_PORT)

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
