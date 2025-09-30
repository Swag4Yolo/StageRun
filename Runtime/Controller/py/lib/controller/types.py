class Engine():
    def __init__(self, engine_key, tag, version, main_file_name, status, comment, zip_path, isa_path, build_path, timestamp,
recirc_ports):
        self.engine_key = engine_key
        self.tag = tag
        self.version = version
        self.main_file_name = main_file_name
        self.status = status
        self.comment = comment
        self.zip_path = zip_path
        self.isa_path = isa_path
        self.build_path = build_path
        self.timestamp = timestamp
        self.recirc_ports = recirc_ports

    @classmethod
    def from_dict(cls, engine_key, dict):
        return cls(
            engine_key = engine_key,
            tag = dict["tag"],
            version = dict["version"],
            main_file_name = dict["main_file_name"],
            status = dict["status"],
            comment = dict["comment"],
            zip_path = dict["zip_path"],
            isa_path = dict["isa_path"],
            build_path = dict["build_path"],
            timestamp = dict["timestamp"],
            recirc_ports = dict["recirc_ports"]
        )

class RunningEngine():
    def __init__(self, engine_key):
        pass

class App():
    def __init__(self, app_key, tag, version, status, comment, timestamp,
app_dir_path, app_path, manifest_path, port_set):
        self.app_key = app_key
        self.tag = tag
        self.version = version
        self.status = status
        self.comment = comment
        self.timestamp = timestamp
        self.app_dir_path = app_dir_path
        self.app_path = app_path
        self.manifest_path = manifest_path
        self.port_set = port_set

    @classmethod
    def from_dict(cls, app_key, dict):
        return cls(
            app_key = app_key,
            tag=dict["tag"],
            version=dict["version"],
            status=dict["status"],
            comment=dict["comment"],
            timestamp=dict["timestamp"],
            app_dir_path=dict["app_dir_path"],
            app_path=dict["app_path"],
            manifest_path=dict["manifest_path"],
            port_set=dict["port_set"]
        )