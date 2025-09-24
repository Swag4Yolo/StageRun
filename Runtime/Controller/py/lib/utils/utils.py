import os
import importlib.util
import json

def load_stagerun_program(filepath, class_name="SystemApp"):
    """
        Load a StageRun Program at runtime.
        More specifically it loads a python file with the code for the installation process.
    """

    module_name = os.path.splitext(os.path.basename(filepath))[0]

    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None:
        raise ImportError(f"Could not load module from {filepath}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(f"Class {class_name} not found in {filepath}")
    
    return cls

def calculate_packet_rates(pattern, total_speed):
    total_size = sum(pattern)
    rates = [int(size / total_size * total_speed) for size in pattern]
    # return rates

    # Example usage
    # pattern = [200, 500, 1000, 1400]
    # total_speed = 10000  # Total speed of the port in Kbps
    # packet_rates = calculate_packet_rates(pattern, total_speed)

    for size, rate in zip(pattern, rates):
        print("Packet size: {} bytes, Rate: {:.2f} Kbps".format(size, rate))

    return rates



def calculate_packet_interval(speed, packet_size_in_bytes, unit='Gbps'):
    # PACKET_SIZE_BYTES = 1500  # Size of each packet in bytes
    PACKET_SIZE_BITS = packet_size_in_bytes * 8  # Convert packet size to bits

    if unit == 'Gbps':
        speed_bps = speed * 1e9  # Convert Gbps to bps
    elif unit == 'Mbps':
        speed_bps = speed * 1e6  # Convert Mbps to bps
    elif unit == 'Kbps':
        speed_bps = speed * 1e3  # Convert Kbps to bps
    else:
        raise ValueError("Unit must be 'Gbps', 'Mbps', or 'Kbps'")

    time_interval_seconds = PACKET_SIZE_BITS / speed_bps  # Time interval in seconds
    time_interval_nanoseconds = time_interval_seconds * 1e9  # Convert to nanoseconds

    return int(round(time_interval_nanoseconds))

def parse_json(json_path:str) -> json:
    with open(json_path) as f:
        return json.load(f)


# def calculate_pps_interval(pps):
#     """
#     Calculate the interval in nanoseconds between packets to achieve the specified pps.
    
#     Parameters:
#     pps (int): Packets per second.
#     packet_size_bytes (int): Size of each packet in bytes.
    
#     Returns:
#     int: Interval in nanoseconds between packets.
#     """
#     # Calculate the interval in seconds
#     interval_seconds = 1 / pps
    
#     # Convert the interval to nanoseconds
#     interval_nanoseconds = interval_seconds * 1e9
    
#     return int(interval_nanoseconds)

# def calculate_bandwidth_kbps(pps, packet_size_bytes):
#     """
#     Calculate the bandwidth in kilobits per second (kbps).
    
#     Parameters:
#     pps (int): Packets per second.
#     packet_size_bytes (int): Size of each packet in bytes.
    
#     Returns:
#     float: Bandwidth in kilobits per second (kbps).
#     """
#     # Calculate bandwidth in kbps
#     bandwidth_kbps = (pps * packet_size_bytes * 8) / 1000
    
#     return bandwidth_kbps

