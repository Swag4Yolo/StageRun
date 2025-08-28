import cmd
import requests
import yaml
import traceback
import os
import argparse

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

    def do_exit(self, line):
        """Exit the client"""
        print("Exiting...")
        return True   # returning True cleanly exits cmd loop

    def do_upload_engine(self, arg):
        """
        Upload an engine to the controller.

        Usage: upload_engine -z <zip_file> -t <tag> -v <version> -m <main_file_name> -c <COMMENT>
        """

        parser = argparse.ArgumentParser(prog="upload_engine")
        parser.add_argument("-z", "--zip", dest="zip_file", help="Path to the engine zip file", required=True)
        parser.add_argument("-t", dest="tag", help="Unique tag identifying the engine", required=True)
        parser.add_argument("-v", dest="version", help="Engine version string", default="v0.1")
        parser.add_argument("-m", dest="main_file_name", help="Main P4 file name to check", required=True)
        parser.add_argument("-c", "--comment", dest="comment", help="Optional comment", default="")

        try:
            args = parser.parse_args(arg.split())

            if not os.path.exists(args.zip_file):
                print(f"Error: File {args.zip_file} does not exist")
                return

            files = {"zip_file": open(args.zip_file, "rb")}
            data = {
                "tag": args.tag,
                "version": args.version,
                "main_file_name": args.main_file_name,
                "comment": args.comment,
            }

            resp = requests.post(f"{self.base_url}/upload_engine", files=files, data=data)
            print(resp.json())

        except SystemExit:
            # argparse throws SystemExit on error; catch it to avoid exiting client
            parser.print_help()
            
        except Exception:
            traceback.print_exc()

    def do_list_engines(self, line):
        """
        List all engines stored on the controller.

        Usage: list_engines
        """
        try:
            resp = requests.get(f"{self.base_url}/list_engines")
            if resp.status_code == 200:
                engines = resp.json()
                print("Engines on controller:")
                for tag, info in engines.items():
                    print(f"- {tag} (version={info['version']}, status={info['status']})")
            else:
                print("Error:", resp.text)
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    StageRunClient().cmdloop()
