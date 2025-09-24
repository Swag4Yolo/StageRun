import cmd
import requests
import yaml
import traceback
import os
import argparse
import re
import shlex

COMPILATION_LOGS_DIR_PATH = None
VERSION_PATTERN = r'^\d+\.\d+$'

class StageRunClient(cmd.Cmd):
    system_name = "StageRun"

    intro = f"""
---------- {system_name} client starts!! ----------
    """
    prompt = f'{system_name}> '

    def __init__(self, config_file='../config.yaml'):
        super().__init__()

        global COMPILATION_LOGS_DIR_PATH


        # Load server config from YAML
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.host = config["server"].get("host", "127.0.0.1")
            self.port = config["server"].get("port", 1337)
            self.base_url = f"http://{self.host}:{self.port}"

            COMPILATION_LOGS_DIR_PATH = config['compilation_log_dir']
            os.makedirs(COMPILATION_LOGS_DIR_PATH, exist_ok=True)
            
        except Exception as e:
            print("Error loading config file:", e)
            exit(1)

    # -------- Commands -------- #
    def do_exit(self, line):
        """Exit the client"""
        print("Exiting...")
        return True   # returning True cleanly exits cmd loop

    # Engines

    def do_upload_engine(self, arg):
        """
        Upload an engine to the controller.

        Usage: upload_engine -z <zip_file> -i <isa_file> -t <tag> -v <version> -m <main_file_name> -c <COMMENT>
        """

        parser = argparse.ArgumentParser(prog="upload_engine")
        parser.add_argument("-z", "--zip", dest="zip_file", help="Path to the engine zip file", required=True)
        parser.add_argument("-i", "--isa", dest="isa_file", help="Path to the engine ISA JSON file", required=True)  # NEW
        parser.add_argument("-t", "--tag", dest="tag", help="Unique tag identifying the engine", required=True)
        parser.add_argument("-v", "--version", dest="version", help="Engine version string", default="0.1")
        parser.add_argument("-m", "--main_file_name", dest="main_file_name", help="Main P4 file name to check", required=True)
        parser.add_argument("-c", "--comment", type=str, dest="comment", help="Optional comment", default="")

        try:
            args = parser.parse_args(shlex.split(arg))

            if not os.path.exists(args.zip_file):
                print(f"Error: File {args.zip_file} does not exist")
                return
            if not os.path.exists(args.isa_file):
                print(f"Error: File {args.isa_file} does not exist")
                return

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return

            files = {
                "zip_file": open(args.zip_file, "rb"),
                "engine_isa": open(args.isa_file, "rb")  # NEW
            }
            data = {
                "tag": args.tag,
                "version": args.version,
                "main_file_name": args.main_file_name,
                "comment": args.comment,
            }

            resp = requests.post(f"{self.base_url}/upload_engine", files=files, data=data)
            print(resp.json())

        except SystemExit:
            pass
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
                for tag, versions in engines.items():
                    print(f"- {tag}:")
                    for version, info in versions.items():
                        status = info.get("status", "UNKNOWN")
                        print(f"    + version {version}: {status}")
                        # print(f"    • version {version}: {status}")
            else:
                print("Error:", resp.text)
        except Exception:
            traceback.print_exc()

    def do_compile_engine(self, arg):
        """
        Compile a previously uploaded engine.
        Usage: compile_engine -t <tag> -v <version> -f "FLAG1 FLAG2 FLAG3=VALUE"
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="Engine tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="Engine version")
        parser.add_argument("-f", "--flags", dest="flags", type=str, default="", help="Compile-time flags")

        try:
            args = parser.parse_args(shlex.split(arg))

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return

            # Send flags to server
            response = requests.post(
                f"{self.base_url}/compile_engine",
                params={
                    "tag": args.tag,
                    "version": args.version,
                    "flags": args.flags.strip()
                }
            )

            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    print(f"Compilation failed: {data['error']}")
                    if "log_path" in data:
                        print(f"See log at: {data['log_path']}")
                        if "log" in data:
                            filepath = os.path.join(COMPILATION_LOGS_DIR_PATH, f"{args.tag}.log")
                            with open(filepath, "w") as f:
                                f.write(data["log"])
                            print(f"Log saved locally at: {filepath}")
                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except SystemExit:
            pass
        except Exception as e:
            print("Error:", e)
            traceback.print_exc()


    def do_install_engine(self, arg):
        """
        Install a previously compiled engine.
        Usage: install_engine -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="Engine tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="Engine version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return
            
            response = requests.post(f"{self.base_url}/install_engine", params={"tag": args.tag, "version": args.version})


            if response.status_code == 200:
                data = response.json()
                if "status" in data and "error" in data["status"]:
                    print(f"Installation failed:")
                    if "message" in data:
                        print(f"Message: {data['message']}")
                    if "log_path" in data:
                        print(f"See log at: {data['log_path']}")
                        if "log" in data:
                            filepath = os.path.join(COMPILATION_LOGS_DIR_PATH, f"{args.tag}.log")
                            with open(filepath, "w") as f:
                                f.write(data["log"])
                            print(f"Log saved locally at: {filepath}")

                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_uninstall_engine(self, arg):
        """
        Uninstalls a previously installed engine.
        Usage: uninstall_engine
        """

        try:
            
            response = requests.post(f"{self.base_url}/uninstall_engine")


            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    print(f"Installation failed: {data['error']}")
                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_remove_engine(self, arg):
        """
        Removes a previously compiled engine.
        Usage: remove_engine -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="Engine tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="Engine version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return
            
            response = requests.delete(f"{self.base_url}/remove_engine", params={"tag": args.tag, "version": args.version})


            if response.status_code == 200:
                data = response.json()
                print(data)
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()


    # Apps

    def do_upload_app(self, arg):
        """
        Upload an app to the controller.

        Usage: upload_app -a <app_file> -m <manifest_file> -t <tag> -v <version> -c <COMMENT>
        """

        parser = argparse.ArgumentParser(prog="upload_engine")
        parser.add_argument("-a", "--app_file", dest="app_file", help="Path to the app zip file", required=True)
        parser.add_argument("-m", "--manifest_file", dest="manifest_file", help="Path to the app zip file", required=True)
        parser.add_argument("-t", "--tag", dest="tag", help="Unique tag identifying the engine", required=True)
        parser.add_argument("-v", "--version", dest="version", help="Engine version string", default="0.1")
        parser.add_argument("-c", "--comment", type=str, dest="comment", help="Optional comment", default="")

        try:
            args = parser.parse_args(shlex.split(arg))

            if not os.path.exists(args.app_file):
                print(f"Error: File {args.app_file} does not exist")
                return
            
            if not os.path.exists(args.manifest_file):
                print(f"Error: File {args.manifest_file} does not exist")
                return
            
            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return

            files = {"app_file": open(args.app_file, "rb"), "manifest_file":open(args.manifest_file, "rb")}
            data = {
                "tag": args.tag,
                "version": args.version,
                "comment": args.comment,
            }

            resp = requests.post(f"{self.base_url}/upload_app", files=files, data=data)
            print(resp.json())

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_list_apps(self, line):
        """
        List all apps stored on the controller.

        Usage: list_apps
        """
        try:
            resp = requests.get(f"{self.base_url}/list_apps")
            if resp.status_code == 200:
                apps = resp.json()
                print("Apps on controller:")
                for tag, versions in apps.items():
                    print(f"- {tag}:")
                    for version, info in versions.items():
                        status = info.get("status", "UNKNOWN")
                        print(f"    + version {version}: {status}")
                        # print(f"    • version {version}: {status}")
            else:
                print("Error:", resp.text)
        except Exception:
            traceback.print_exc()

    def do_remove_app(self, arg):
        """
        Removes a previously compiled engine.
        Usage: remove_app -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="Engine tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="Engine version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return
            
            response = requests.delete(f"{self.base_url}/remove_app", params={"tag": args.tag, "version": args.version})


            if response.status_code == 200:
                data = response.json()
                print(data)
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_install_app(self, arg):
        """
        Install a previously uploaded app.
        Usage: install_app -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="App tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="App version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return
            
            response = requests.get(f"{self.base_url}/install_app", params={"tag": args.tag, "version": args.version})


            if response.status_code == 200:
                data = response.json()
                if "status" in data and "error" in data["status"]:
                    print(f"Installation failed:")
                    print(data.get("message"))

                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_run_app(self, arg):
        """
        Install a previously uploaded app.
        Usage: run_app -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="App tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="App version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return

            import time            
            start_time = time.perf_counter()

            response = requests.get(f"{self.base_url}/run_app", params={"tag": args.tag, "version": args.version})
            
            # Record finish time


            if response.status_code == 200:
                finish_time = time.perf_counter()
                # Compute elapsed time
                time_diff = finish_time - start_time
                print(f"Function took {time_diff:.6f} seconds")

                data = response.json()
                if "status" in data and "error" in data["status"]:
                    print(f"Installation failed:")
                    print(data.get("message"))

                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()

    def do_uninstall_app(self, arg):
        """
        Install a previously uploaded app.
        Usage: uninstall_app -t <tag> -v <version>
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tag", dest="tag", type=str, required=True, help="App tag")
        parser.add_argument("-v", "--version", dest="version", type=str, required=True, help="App version")

        try:
            args = parser.parse_args(arg.split())

            if not re.fullmatch(VERSION_PATTERN, args.version):
                print(f"Error: Version must contain only digits such as '31.01' instead of '{args.version}'")
                return
            
            response = requests.get(f"{self.base_url}/uninstall_app", params={"tag": args.tag, "version": args.version})


            if response.status_code == 200:
                data = response.json()
                if "status" in data and "error" in data["status"]:
                    print(f"Uninstall failed:")
                    print(data.get("message"))

                else:
                    print(data.get("message"))
            else:
                print(f"Server returned status {response.status_code}: {response.text}")

        except Exception as e:
            print("Error:", e)

        except SystemExit:
            pass
            
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    StageRunClient().cmdloop()
