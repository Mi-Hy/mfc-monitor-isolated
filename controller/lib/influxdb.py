from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
from datetime import datetime, timezone
import os
import re
import shutil
import glob

# from configuration import *

# Directory with latest results
result_vna_dir = os.path.join(os.getcwd(), "results/vna")

# Directory with backup results
result_vna_backup_dir = os.path.join(os.getcwd(), "results/vna_backup")

#   Init lists
frequencies = []
reals = []
imags = []
number_of_points = 0

def get_oldest_file(debug_name):
    files = [os.path.join(result_vna_dir, f) for f in os.listdir(result_vna_dir) if os.path.isfile(os.path.join(result_vna_dir, f))]

    if files:
        oldest_file = min(files, key=os.path.getmtime)
        # print("📄 File:", oldest_file)
        debug(debug_name, f"📄 File: {oldest_file}")
        return oldest_file
    else:
        # print("⚠️ No files found", result_vna_dir)
        debug(debug_name, f"⚠️ No files found {result_vna_dir}")
        return ""
    

def retrieve_data_from_file(file):

    with open(file, "r") as file:
        for line in file:
            try:
                freq_str, complex_str = line.strip().split(";")
                freq = float(freq_str)

                # Verwijder haakjes en zet om naar complex getal
                complex_val = complex(complex_str.replace("(", "").replace(")", ""))
                
                # Waarden toevoegen aan lijsten
                frequencies.append(freq)
                reals.append(complex_val.real)
                imags.append(complex_val.imag)
            except Exception as e:
                print(f"⚠️ Error processing rule: {line.strip()} → {e}")


def find_timestamp_in_filename(file_path):
    filename = os.path.basename(file_path)

    # Search file name
    match = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", filename)
    if match:
        timestamp_str = match.group()
        # Convert to datetime
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")

        # Parse to datetime object
        ts = datetime.strptime(str(dt), '%Y-%m-%d %H:%M:%S')

        # Convert to ISO 8601 with 'Z' suffix before UTC (Z = Zulu Time = UTC)
        ts_influx = ts.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        ts_influx = None
        print("❌ No timestamp found")

    return ts_influx

def find_polarisation_in_filename(file_path):
    filename = os.path.basename(file_path)

    # Search for _VV of _VH in filename
    match = re.search(r"_([A-Z]{2})\.txt$", filename)
    if match:
        polarisation = match.group(1)
        # print("📡 Polarisation found:", polarisation)
    else:
        print("❌ No polarisation found")
        polarisation = ""
    
    return polarisation


def debug(debug_name, string):
    print(f"{debug_name} {string}")


def send_system_info(config, debug_name, temperature_data, system_data, water_quality):

    client = InfluxDBClient(url=config['influxdb']['url'], token=config['influxdb']['token'], org=config['influxdb']['org'])

    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Timestamp
    ts = datetime.now()

    # Create point
    point = (
        Point("system_data")
        .time(ts)
        .tag("device", config['fixed_configurations']['device_name'])
        .field("temp", float(temperature_data["temp"]))
        .field("system-cpu-temp", system_data["system-cpu-temp"])
        .field("system-cpu-load", system_data["system-cpu-load"])
        .field("system-disk", system_data["system-disk"])
        .field("DO", water_quality["DO"])
        .field("PH", water_quality["PH"])
        .field("EC", water_quality["EC"])
        .field("RTD", water_quality["RTD"])
    )
    print(point)
    # Write data in batch
    try:
        write_api.write(bucket=config['influxdb']['bucket'], org=config['influxdb']['org'], record=point)
        debug(debug_name, f"✓ System data sended.")
    except Exception as e:
        debug(debug_name, f"[Warning] Could not write to InfluxDB: {e}")
        client.close()
        return False

    client.close()


def send_power_sensors_info(config, debug_name, voltage_data, current_data):

    client = InfluxDBClient(url=config['influxdb']['url'], token=config['influxdb']['token'], org=config['influxdb']['org'])

    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Timestamp
    ts = datetime.now()

    points = []

    for cell, voltage in voltage_data.items():
        point = (
            Point("cell_measurements")
            .time(ts)
            .tag("device", config['fixed_configurations']['device_name'])
            .tag("cell", cell)
            .field("voltage", voltage)
            .field("current", current_data.get(cell, 0))
        )
        points.append(point)


    # Write data in batch
    try:
        write_api.write(bucket=config['influxdb']['bucket'], org=config['influxdb']['org'], record=points)
        debug(debug_name, f"✓ System data sended.")
    except Exception as e:
        debug(debug_name, f"[Warning] Could not write to InfluxDB: {e}")
        client.close()
        return False

    client.close()


def send_voltage_info(config, debug_name, voltage_data):

    client = InfluxDBClient(url=config['influxdb']['url'], token=config['influxdb']['token'], org=config['influxdb']['org'])

    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Timestamp
    ts = datetime.now()

    points = []

    for cell, voltage in voltage_data.items():
        point = (
            Point("voltage_data")
            .time(ts)
            .tag("device", config['fixed_configurations']['device_name'])
            .tag("cell", cell)
            .field("voltage", voltage)
        )
        points.append(point)

    # Write data in batch
    try:
        write_api.write(bucket=config['influxdb']['bucket'], org=config['influxdb']['org'], record=points)
        debug(debug_name, f"✓ System data sended.")
    except Exception as e:
        debug(debug_name, f"[Warning] Could not write to InfluxDB: {e}")
        client.close()
        return False

    client.close()


def send_load_info(config, debug_name, load_data, target_load, cell_index):

    client = InfluxDBClient(url=config['influxdb']['url'], token=config['influxdb']['token'], org=config['influxdb']['org'])

    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Timestamp
    ts = datetime.now()

    # Create point
    point = (
        Point("load_data")
        .time(ts)
        .tag("device", config['fixed_configurations']['device_name'])
        .tag("target_load", str(target_load))
        .tag("cell", str(cell_index))
    )

    for key, value in load_data.items():
        point.field(key, value)

    # Write data in batch
    try:
        write_api.write(bucket=config['influxdb']['bucket'], org=config['influxdb']['org'], record=point)
        debug(debug_name, f"✓ System data sended.")
    except Exception as e:
        debug(debug_name, f"[Warning] Could not write to InfluxDB: {e}")
        client.close()
        return False

    client.close()