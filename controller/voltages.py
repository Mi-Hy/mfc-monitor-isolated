import time
from statistics import median

import board
from adafruit_ina219 import INA219, Gain

from lib.influxdb import *
from lib.denkovi_relay import *
from lib.configuration import *

import RPi.GPIO as GPIO


CELLS = 8

# INA219 I2C addresses
INA219_ADDRESSES = [
    0x40,
    0x41,
    0x42,
    0x43,
    0x44,
    0x45,
    0x46,
    0x47
]



# -------------------------------------------------------------------------
# I2C initialiseren
# -------------------------------------------------------------------------

i2c = board.I2C()


# -------------------------------------------------------------------------
# INA219 initialiseren
# -------------------------------------------------------------------------

ina219_devices = []

for address in INA219_ADDRESSES:

    ina219 = INA219(i2c, addr=address)

    # Maximale gevoeligheid:
    # ±40 mV shunt-voltage range
    ina219.gain = Gain.DIV_1_40MV

    # Shuntweerstand = 100 mΩ
    ina219.shunt_resistance = 0.1

    ina219_devices.append(ina219)

    print(f"INA219 initialized at 0x{address:02X}")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

if __name__ == "__main__":

    # Get config file
    config = retrieve_yaml_file()

    while config['activity']['load'] == 1:

        print("[Voltage] ⏳ Waiting for load test to complete...")

        time.sleep(5)

        config = retrieve_yaml_file()

    update_yaml_flag("activity", "voltage", 1)

    voltage_buffer = []


    for i in range(CELLS):


        # -------------------------------------------------------------
        # Select cell using Denkovi relay
        # -------------------------------------------------------------

        time.sleep(0.1)

        # -------------------------------------------------------------
        # Read corresponding INA219
        #
        # Cell 1 -> 0x40
        # Cell 2 -> 0x41
        # ...
        # Cell 8 -> 0x47
        # -------------------------------------------------------------

        ina219 = ina219_devices[i]

        buffer_voltages = []

        for _ in range(5):

            try:

                voltage = ina219.bus_voltage

                # Convert V -> mV
                voltage_mv = voltage * 1000

                buffer_voltages.append(voltage_mv)

            except Exception as e:

                print(
                    f"[Cell {i + 1}] "
                    f"INA219 read error: {e}"
                )

            time.sleep(0.05)

        # -------------------------------------------------------------
        # Median of the 5 measurements
        # -------------------------------------------------------------

        if buffer_voltages:

            buffer_voltage_median = median(buffer_voltages)

            print(
                f"[Cell {i + 1}] "
                f"INA219 0x{INA219_ADDRESSES[i]:02X} "
                f"Buffer Voltage: "
                f"{buffer_voltage_median:.1f} mV"
            )

            voltage_buffer.append(
                int(round(buffer_voltage_median))
            )

        else:

            print(
                f"[Cell {i + 1}] "
                f"Could not read INA219"
            )

            voltage_buffer.append(0)




# -------------------------------------------------------------------------
# Process voltage data
# -------------------------------------------------------------------------

device_mode = config.get(
    "measurement_mode",
    {}
).get(
    "device_mode",
    "individual"
)

print("CELLS:", CELLS)
print("voltage_buffer:", voltage_buffer)
print("length:", len(voltage_buffer))


try:

    if device_mode == "series":

        voltage_data = {}

        previous = 0

        for i in range(CELLS):

            voltage_data[f"cell_{i}"] = (
                voltage_buffer[i] - previous
            )

            previous = voltage_buffer[i]

    else:

        voltage_data = {
            f"cell_{i}": voltage_buffer[i]
            for i in range(CELLS)
        }

except IndexError as e:

    print(f"Voltage buffer index error: {e}")

    voltage_data = {}


# -------------------------------------------------------------------------
# Send voltage information
# -------------------------------------------------------------------------

if voltage_data:

    send_voltage_info(
        config,
        "[Voltage]",
        voltage_data
    )


update_yaml_flag("activity", "voltage", 0)
