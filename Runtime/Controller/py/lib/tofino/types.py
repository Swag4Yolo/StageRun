import inspect

# class TernaryMatch():
#     def __init__(self, value=0, mask=0):
#         self.value = value
#         self.mask = mask

# class ExactMatch():
#     def __init__(self, value=0):
#         self.value = value

class BaseTableKeys:
    """
    Base class for table keys.
    Provides a common interface for converting key values to the runtime format.
    """
    def __init__(self):
        self.annotations = []

    def to_key_list(self):
        raise NotImplementedError("Subclasses must implement the 'to_key_list' method.")

class BaseAction:
    def __init__(self, name, *args):
        # Retrieve the names of the variables passed as arguments
        
        frame = inspect.currentframe().f_back  # Get caller's frame
        arg_names = [name for name in inspect.getframeinfo(frame).code_context[0].split('(', 1)[1].split(')')[0].split(', ')[1:]]

        # Store the action information in a dict
        self.action_params = {
            "action_name": name,
            "params": {arg_name: arg for arg_name, arg in zip(arg_names, args)}
        }

class BaseTable:
    """
    Base class for tables.
    Encapsulates common functionality like adding entries and handling actions.
    """

    def __init__(self, runtime, table_name):
        self.runtime = runtime
        self.table_name = table_name
        self.entries = []

    def __verify__action__(self, action:BaseAction):
        action_params = action.action_params

        if "action_name" not in action_params or "params" not in action_params:
            raise ValueError("Invalid action parameters. Ensure they are returned by an action method.")

        return action_params["action_name"], action_params["params"]

    def add_entry(self, keys: BaseTableKeys, action:BaseAction):
        """
        Add an entry to the table.
        :param keys: An instance of a subclass of BaseTableKeys.
        :param action_params: A dictionary returned by an action method.
        """
        # Convert keys to the required format
        key_list = keys.to_key_list()

        action_name, params = self.__verify__action__(action)
        # Prepare the action parameters
        action_params_list = [[name, value] for name, value in params.items()]
        

        # Add the entry
        self.runtime.__entry_add__(self.table_name, key_list, [action_params_list, action_name], keys.annotations)

    def clear_table(self):
        """
        """
        self.runtime.__table_clear__(self.table_name)

    def get_entry(self, keys: BaseTableKeys, from_hw):
        """
        Add an entry to the table.
        :param keys: An instance of a subclass of BaseTableKeys.
        :param action_params: A dictionary returned by an action method.
        """
        # Convert keys to the required format
        key_list = keys.to_key_list()

        # Add the entry
        return self.runtime.__entry_get__(self.table_name, key_list, from_hw)

    def set_default_entry(self, action:BaseAction):
        action_name, params = self.__verify__action__(action)
        # Prepare the action parameters
        action_params_list = [[name, value] for name, value in params.items()]
        
        self.runtime.__entry_set_default__(self.table_name, [action_params_list, action_name])


    def default_entry_reset(self):
        raise NotImplementedError("Not Tested Yet")
        self.runtime.__entry_reset__(self.table_name)

class Program():
    def __init__(self, program_id=1, program_name='Not Specified'):
        self.pid = program_id
        self.name = program_name
        self.ports = []
        
        self.wp_s3=0
        self.wp_s4=0
        self.wp_s5=0
        self.wp_s6=0
        self.wp_s7=0
        self.wp_s8=0
        self.wp_s9=0
        self.wp_s10=0

    def set_write_phases(self, write_s3=0, write_s4=0, write_s5=0, write_s6=0, write_s7=0, write_s8=0, write_s9=0, write_s10=0):
        self.wp_s3=write_s3
        self.wp_s4=write_s4
        self.wp_s5=write_s5
        self.wp_s6=write_s6
        self.wp_s7=write_s7
        self.wp_s8=write_s8
        self.wp_s9=write_s9
        self.wp_s10=write_s10