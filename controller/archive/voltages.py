from statistics import median

from lib.ep_handler import *
from lib.influxdb import *
from lib.denkovi_relay import *
from lib.configuration import *

io = DenkoviRelay()

CELLS = 8

def get_ep_data_retry(max_attempts=3, delay=0.5):
    for attempt in range(max_attempts):
        try:
            ep_data = get_ep_data()
            return ep_data

        except IndexError as e:
            print(f"EP read failed (attempt {attempt+1}/{max_attempts}): {e}")
            time.sleep(delay)

    print("EP read failed after multiple attempts")
    return None

import RPi.GPIO as GPIO

BUFFER_RELAY_PIN = 19  # GPIO19 = fysieke pin 35

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUFFER_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)


if __name__ == "__main__":

    # Get config file
    config = retrieve_yaml_file()

    while(config['activity']['load'] == 1):
        #   Debug message
        print("[Voltage] ⏳ Waiting for load test to complete...")
        
        #   Wait 5 seconds before checking again
        time.sleep(5)

        #   Update config file to indicate voltage test is running
        config = retrieve_yaml_file()

    update_yaml_flag("activity", "voltage", 1)

    ep_change_resistance(0)

    time.sleep(3)

    # while True:

    voltage_buffer = []

    try:

        for i in range(CELLS):

            GPIO.output(BUFFER_RELAY_PIN, GPIO.HIGH)

            time.sleep(0.5)

            io.relay_on(i + 1)

            time.sleep(0.1)

            # ep_data = get_ep_data_retry(max_attempts = 10)

            buffer_voltages = []

            for _ in range(5):
                ep_data = get_ep_data_retry(max_attempts=10)
                if ep_data is not None:
                    buffer_voltages.append(float(ep_data.get("buffer_voltage_mv", 0)))

            buffer_voltage_median = median(buffer_voltages)

            # print(ep_data)

            print(f"[Cell {i + 1}] Buffer Voltage: {buffer_voltage_median} mV")

            voltage_buffer.append(int(buffer_voltage_median))

            time.sleep(0.1)

            io.relay_off(i + 1)

            time.sleep(0.1)

            GPIO.output(BUFFER_RELAY_PIN, GPIO.LOW)

            time.sleep(1)

    finally:
        GPIO.cleanup()
    
    # voltage_data = {f"cell_{i}": voltage_buffer[i] for i in range(CELLS)}

    # Check device mode and calculate voltage data accordingly
    device_mode = config.get("measurement_mode", {}).get("device_mode", "individual")

    print("CELLS:", CELLS)
    print("voltage_buffer:", voltage_buffer)
    print("length:", len(voltage_buffer))

    try:
        if device_mode == "series":
            voltage_data = {}
            previous = 0

            for i in range(CELLS):
                voltage_data[f"cell_{i}"] = voltage_buffer[i] - previous
                previous = voltage_buffer[i]
        else:
            voltage_data = {
                f"cell_{i}": voltage_buffer[i]
                for i in range(CELLS)
            }

    except IndexError as e:
        print(f"Voltage buffer index error: {e}")
        voltage_data = {}

    if voltage_data:
        send_voltage_info(config, "[Voltage]", voltage_data)

    update_yaml_flag("activity", "voltage", 0)
