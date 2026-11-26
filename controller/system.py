
import yaml
import time
import psutil
import subprocess
from lib.influxdb import *
from lib.configuration import *
import asyncio
import socket
from lib.ds18b20 import *
# from lib.socket_helper import *
# from atlas_scientific.poll import *
from lib.sensors import *
from lib.i2c_manager import *

def get_cpu_temp():
    try:
        output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
        return float(output.replace("temp=", "").replace("'C\n", ""))
    except Exception:
        return None

def get_cpu_load():
    try:
        return psutil.cpu_percent(interval=1)
    except Exception:
        return None

def get_disk_usage():
    try:
        usage = psutil.disk_usage('/')
        return round(usage.percent, 2)  # in %
    except Exception:
        return None 

if __name__ == "__main__":

    system_data = {
        "system-cpu-temp": get_cpu_temp(),
        "system-cpu-load": get_cpu_load(),
        "system-disk": get_disk_usage()
    }

    # Get config file
    config = retrieve_yaml_file()

    # Read DS18B20 sensors
    try:
        ds18b20 = read_ds18b20_sensors()
    except Exception as e:
        print(e)

    # Create dict wih temperature data
    temperature_data = {
        "temp": ds18b20[0],
    }

    with SMBus(I2C_BUS) as bus:
        # Avoid conflicts with other I2C devices by disconnecting the water quality sensors before reading INA219 and INA226 sensors
        connect_water_quality_sensors(bus)

        if config.get("sensor_configurations", {}).get("temp_compensation", 0) == 0:
            water_quality = read_all_once()
        else:
            water_quality = read_all_once_temp_compensated()

        if water_quality is None:
            water_quality = {
                "ph": 0,
                "ec": 0,
                "do": 0,
                "orp": 0
            }

        # Allow other I2C devices to be used again by disconnecting the water quality sensors
        disconnect_water_quality_sensors()

    print("System data:", system_data)
    print("Temperature data:", temperature_data)
    print("Water quality sensors:", water_quality)

    # Send data to influxdb server
    send_system_info(config, "[System]", temperature_data, system_data, water_quality)