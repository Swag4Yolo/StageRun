import yaml
import re

class EndpointInfo():
    def __init__(self, name:str=None, port:int=None):
        self.name = name 
        self.port = port

# def parse_manifest(manifest_path: str):

#     # Read the YAML data from the file
#     with open(manifest_path, 'r') as file:
#         yaml_data = file.read()

#     # Parse the YAML data into a Python dictionary
#     return yaml.safe_load(yaml_data)

def parse_manifest(manifest_path: str):
    with open(manifest_path, 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Normalize ports
    ports = yaml_data.get("switch", {}).get("ports", None)
    if isinstance(ports, list):
        normalized = {}
        for entry in ports:
            normalized.update(entry)
        yaml_data["switch"]["ports"] = normalized

    return yaml_data

def get_endpoints(manifest):
    raw_endpoints = manifest['program']['Endpoints']
    endpoints = []
    for name,v in raw_endpoints.items():
        p_num = int(re.search('[0-9]+', v['port'])[0])
        endpoints.append(EndpointInfo(name, p_num))
    return endpoints

def get_pnum_from_endpoints(manifest, port_name):
    port_str = manifest['program']['Endpoints'][port_name]['port']
    return int(re.search('[0-9]+', port_str)[0])
