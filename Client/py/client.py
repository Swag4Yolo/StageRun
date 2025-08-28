import cmd
import requests
import yaml
import traceback

class StageRunClient(cmd.Cmd):
    system_name = "StageRun"

    intro = f"""
---------- {system_name} client starts!! ----------
    """
    prompt = f'{system_name}> '

    def __init__(self, config_file='../config.yaml'):
        super().__init__()

        # Load server config from YAML
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.host = config["server"].get("host", "127.0.0.1")
            self.port = config["server"].get("port", 1337)
            self.base_url = f"http://{self.host}:{self.port}"
        except Exception as e:
            print("Error loading config file:", e)
            exit(1)

    # -------- Commands -------- #

    def do_install_engine(self, line):
        """install_engine ENGINE_NAME -- Install a new engine"""
        engine_name = line.strip()
        if not engine_name:
            print("Usage: install_engine ENGINE_NAME")
            return

        try:
            resp = requests.post(f"{self.base_url}/install_engine", json={"engine_name": engine_name})
            data = resp.json()
            print(f"[Server] {data['status']}: {data['msg']}")
        except Exception as e:
            print("Error communicating with server:", e)
            traceback.print_exc()

    def do_compile_engine(self, line):
        """compile_engine ENGINE_NAME -- Compile an engine"""
        engine_name = line.strip()
        if not engine_name:
            print("Usage: compile_engine ENGINE_NAME")
            return

        try:
            resp = requests.post(f"{self.base_url}/compile_engine", json={"engine_name": engine_name})
            data = resp.json()
            print(f"[Server] {data['status']}: {data['msg']}")
        except Exception as e:
            print("Error communicating with server:", e)
            traceback.print_exc()

    def do_exit(self, line):
        """Exit the client"""
        print("Exiting...")
        return True   # returning True cleanly exits cmd loop


if __name__ == "__main__":
    StageRunClient().cmdloop()
