import subprocess
import time
from datetime import datetime, timedelta, timezone
import yaml
import os
from lib.scheduler import Scheduler
from filelock import FileLock
from lib.influxdb import *
from lib.configuration import *
from lib.sensors import *
from lib.i2c_manager import *
from lib.cv_load import *

import socket
import threading
import json

# Booleans
socket_server_started = False

# Config
system_script_path = "system.py"
voltage_script_path = "cell_measurements.py"
load_script_path = "load.py"

# Initial start time
start_time = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Initial interval
system_interval = timedelta(hours=0, minutes=1, seconds=0)
voltage_interval = timedelta(hours=0, minutes=1, seconds=0)
load_interval = timedelta(hours=0, minutes=1, seconds=0)

# Countdown variables in YAML
rpi_date_time = ["rpi_year", "rpi_month", "rpi_day","rpi_hour", "rpi_minute", "rpi_second"]
sys_countdown_vars = ["sys_countdown_hour", "sys_countdown_minute", "sys_countdown_second"]
volt_countdown_vars = ["volt_countdown_hour", "volt_countdown_minute", "volt_countdown_second"]
load_countdown_vars = ["load_countdown_hour", "load_countdown_minute", "load_countdown_second"]

# Init schedulers
system_scheduler = Scheduler("System", system_script_path, start_time, system_interval, sys_countdown_vars, False)
voltage_scheduler = Scheduler("Voltage", voltage_script_path, start_time, voltage_interval, volt_countdown_vars, False)
load_scheduler = Scheduler("Load", load_script_path, start_time, load_interval, load_countdown_vars, False)

# *** *** #
SOCKET_PATH = "/tmp/streaming_socket.sock"

def stream_data(conn):
    with conn:
        try:
            now = datetime.now()

            data = {
                rpi_date_time[0]: now.year,
                rpi_date_time[1]: now.month,
                rpi_date_time[2]: now.day,
                rpi_date_time[3]: now.hour,
                rpi_date_time[4]: now.minute,
                rpi_date_time[5]: now.second,
                "sys_activity": system_scheduler.activity,
                sys_countdown_vars[0]: system_scheduler.countdown_remaining // 3600,
                sys_countdown_vars[1]: (system_scheduler.countdown_remaining % 3600) // 60,
                sys_countdown_vars[2]: system_scheduler.countdown_remaining % 60,
                "volt_activity": voltage_scheduler.activity,
                volt_countdown_vars[0]: voltage_scheduler.countdown_remaining // 3600,
                volt_countdown_vars[1]: (voltage_scheduler.countdown_remaining % 3600) // 60,
                volt_countdown_vars[2]: voltage_scheduler.countdown_remaining % 60,
                "load_activity": load_scheduler.activity,
                load_countdown_vars[0]: load_scheduler.countdown_remaining // 3600,
                load_countdown_vars[1]: (load_scheduler.countdown_remaining % 3600) // 60,
                load_countdown_vars[2]: load_scheduler.countdown_remaining % 60
            }
            conn.sendall((json.dumps(data) + "\n").encode())
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"⚠️ Broken connection during transmission: {e}")
        except Exception as e:
            print(f"❌ Unexpected error during transmission: {e}")

def update_system_timer_settings(settings):
    system_interval = timedelta(hours=settings["sys_interval_hour"], minutes=settings["sys_interval_minute"], seconds=settings["sys_interval_second"])

    # Update system scheduler parameters
    system_scheduler.update_parameters(start_time, system_interval)

    # Reschedule next run based on new parameters
    system_scheduler.reschedule_next_run()


def update_voltage_timer_settings(settings):
    voltage_interval = timedelta(hours=settings["volt_interval_hour"], minutes=settings["volt_interval_minute"], seconds=settings["volt_interval_second"])

    # Update voltage scheduler parameters
    voltage_scheduler.update_parameters(start_time, voltage_interval)

    # Reschedule next run based on new parameters
    voltage_scheduler.reschedule_next_run()

def update_load_timer_settings(settings):
    load_interval = timedelta(hours=settings["load_interval_hour"], minutes=settings["load_interval_minute"], seconds=settings["load_interval_second"])

    # Update load scheduler parameters
    load_scheduler.update_parameters(start_time, load_interval)

    # Reschedule next run based on new parameters
    load_scheduler.reschedule_next_run()

def start_server():
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(1)

    print(f"🟢 Server luistert op {SOCKET_PATH}")

    try:
        while True:
            conn, _ = server.accept()
            # print("✅ Client connected")
            t = threading.Thread(target=stream_data, args=(conn,))
            t.daemon = True
            t.start()
    except KeyboardInterrupt:
        print("🛑 Server stopped.")
    finally:
        server.close()
        os.remove(SOCKET_PATH)
# *** *** #


def update_automations(config):
    if config.get("automations", {}).get("auto_sys_poll", 0) == 1:
        system_scheduler.start()
    else:
        system_scheduler.stop()

    if config.get("automations", {}).get("auto_volt_poll", 0) == 1:
        voltage_scheduler.start()
    else:
        voltage_scheduler.stop()   

    if config.get("automations", {}).get("auto_load_poll", 0) == 1:
        load_scheduler.start()
    else:
        load_scheduler.stop()   

def check_sensor_functions(config):

    # Get config file
    config = retrieve_yaml_file()

    # Get activity status from config file
    while get_activity_status() == 1:
        time.sleep(1)
        print("[System] ⏳ Waiting for other scripts to complete...")

    # Update config file to indicate atlas sensor calibration is running
    update_yaml_flag("activity", "atlas_sensor_calibration", 1)

    if config.get("sensor_requests", {}).get("update", 0) == 1:

        connect_water_quality_sensors()

        # pH
        if config.get("sensor_requests", {}).get("ph_cal_req_status", 0) == 1:
            ph_cal()
            update_yaml_flag("sensor_requests", "ph_cal_req_status", 0)

        if config.get("sensor_requests", {}).get("ph_cal_req_clear", 0) == 1:
            ph_cal_clear()
            update_yaml_flag("sensor_requests", "ph_cal_req_clear", 0)

        if config.get("sensor_requests", {}).get("ph_cal_req_low4", 0) == 1:
            ph_cal_low()
            update_yaml_flag("sensor_requests", "ph_cal_req_low4", 0)

        if config.get("sensor_requests", {}).get("ph_cal_req_mid7", 0) == 1:
            ph_cal_mid()
            update_yaml_flag("sensor_requests", "ph_cal_req_mid7", 0)

        if config.get("sensor_requests", {}).get("ph_cal_req_high10", 0) == 1:
            ph_cal_high()
            update_yaml_flag("sensor_requests", "ph_cal_req_high10", 0)

        # Dissolved Oxygen (DO)
        if config.get("sensor_requests", {}).get("do_cal_req_status", 0) == 1:
            do_cal()
            update_yaml_flag("sensor_requests", "do_cal_req_status", 0)

        if config.get("sensor_requests", {}).get("do_cal_req_clear", 0) == 1:
            do_cal_clear()
            update_yaml_flag("sensor_requests", "do_cal_req_clear", 0)

        if config.get("sensor_requests", {}).get("do_cal_req_aol", 0) == 1:
            do_cal_aol()
            update_yaml_flag("sensor_requests", "do_cal_req_aol", 0)

        if config.get("sensor_requests", {}).get("do_cal_req_null", 0) == 1:
            do_cal_null()
            update_yaml_flag("sensor_requests", "do_cal_req_null", 0)

        # Electrical Conductivity (EC)
        if config.get("sensor_requests", {}).get("ec_cal_req_status", 0) == 1:
            ec_cal()
            update_yaml_flag("sensor_requests", "ec_cal_req_status", 0)

        if config.get("sensor_requests", {}).get("ec_cal_req_clear", 0) == 1:
            ec_cal_clear()
            update_yaml_flag("sensor_requests", "ec_cal_req_clear", 0)

        if config.get("sensor_requests", {}).get("ec_cal_req_dry", 0) == 1:
            ec_cal_dry()
            update_yaml_flag("sensor_requests", "ec_cal_req_dry", 0)

        if config.get("sensor_requests", {}).get("ec_cal_req_one", 0) == 1:
            ec_cal_one()
            update_yaml_flag("sensor_requests", "ec_cal_req_one", 0)

        if config.get("sensor_requests", {}).get("ec_cal_req_low", 0) == 1:
            ec_cal_low()
            update_yaml_flag("sensor_requests", "ec_cal_req_low", 0)

        if config.get("sensor_requests", {}).get("ec_cal_req_high", 0) == 1:
            ec_cal_high()
            update_yaml_flag("sensor_requests", "ec_cal_req_high", 0)

    # Disable update flag
    if get_sensor_req_status() == 0:
        # Update flag in config file
        update_yaml_flag("sensor_requests", "update", 0)

        # Disable activity flag
        update_yaml_flag("activity", "atlas_sensor_calibration", 0)       

    # Disconnect water quality sensors to avoid conflicts with other I2C devices
    disconnect_water_quality_sensors()

def check_cv_load_settings(config):

    # Check if CV Load settings have changed and if no other script is running
    if config.get("cv_load", {}).get("update", 0) == 1:

        print("There is an update in the CV Load settings. Checking if any other script is running...")

        if get_activity_status() == 0:

            print("CV Load settings changed!")

            # Update flag in config file to indicate CV Load adjustment is in progress
            update_yaml_flag("activity", "adjusting_cv_load", 1)

            # Update CV Load settings
            update_cv_load(config["cv_load"])

            # Update flag in config file to indicate CV Load adjustment is finished
            update_yaml_flag("activity", "adjusting_cv_load", 0)

            # Update flag in config file
            update_yaml_flag("cv_load","update", 0)
        else:
            time.sleep(0.1)  # Sleep briefly to avoid busy waiting


def main_loop():

    #   Load YAML config file
    config = retrieve_yaml_file()

    #   Init auto measurement settings
    update_system_timer_settings(config["timer_settings"])
    update_voltage_timer_settings(config["timer_settings"])
    update_load_timer_settings(config["timer_settings"])

    #   Check device mode and change power settings
    # check_device_mode(config)

    #   Initialisation done
    print("Init done")

    system_scheduler.stop()
    voltage_scheduler.stop()
    load_scheduler.stop()

    #   Do first an update of the automations
    update_automations(config)

    while 1:
        # print(f"System remaining time: {system_scheduler.get_remaining_time()}")
        # print(f"Voltage remaining time: {voltage_scheduler.get_remaining_time()}")
        # # print(f"Load remaining time: {load_scheduler.get_remaining_time()}")
        # time.sleep(10)

        time.sleep(0.1)

        #   Load YAML config file
        config = retrieve_yaml_file()

        #   Check updates in "timer_settings"
        if config.get("timer_settings", {}).get("update", 0) == 1:
            print("Timer settings changed!")

            # Update timer settings temperature measurements
            update_system_timer_settings(config["timer_settings"])

            # Update timer settings voltage measurements
            update_voltage_timer_settings(config["timer_settings"])

            # Update timer settings load measurements
            update_voltage_timer_settings(config["timer_settings"])
            
            # Update flag in config file
            update_yaml_flag("timer_settings","update", 0)


        # Trigger measurement script
        if config.get("trigger", {}).get("system", 0) == 1:
            print("Single system measurement")

            # Execute the script directly without waiting for the scheduler timer
            system_scheduler.start_script()          

            # Clear single measurement trigger flag
            update_yaml_flag("trigger", "system", 0)

        if config.get("trigger", {}).get("voltage", 0) == 1:
            print("Single voltage measurement")

            # Execute the script directly without waiting for the scheduler timer
            voltage_scheduler.start_script()          

            # Clear single measurement trigger flag
            update_yaml_flag("trigger", "voltage", 0)

        if config.get("trigger", {}).get("load", 0) == 1:
            print("Single load measurement")

            # Execute the script directly without waiting for the scheduler timer
            load_scheduler.start_script()          

            # Clear single measurement trigger flag
            update_yaml_flag("trigger", "load", 0)


        if config.get("automations", {}).get("update", 0) == 1:
            print("Automation settings changed!")

            # Update all automations (system/voltage/load)
            update_automations(config)

            # Update flag in config file
            update_yaml_flag("automations","update", 0)

        #   Check hydroponics sensors
        check_sensor_functions(config)

        #   Check CV load settings
        check_cv_load_settings(config)

if __name__ == "__main__":

    # Start thread to start small server
    threading.Thread(target=start_server, daemon=True).start()
    
    main_loop()