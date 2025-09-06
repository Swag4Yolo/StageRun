from .port_mechanism import *
from .runtime import *

class TofinoController():
    """
        Tofino Controller is a class that creates the first inter connection to the Tofino APIs, by providing an initial runtime that allows to manage tables, and ports.
    """
    def __init__(self, engine_key):
        try:
            self.engine_key = engine_key
            self.runtime = bfrt_runtime(0, self.engine_key)
            self.port_mechanism = PortMechanism(self.runtime)
            # self.manager = Manager()
        except Exception as e:
            print(traceback.format_exc())
            # exit(1)

    # def update_engine_key(self, engine_key):
    #     self.engine_key = engine_key
    #     self.runtime = bfrt_runtime(0, self.engine_key)
    #     self.port_mechanism = PortMechanism(self.runtime)