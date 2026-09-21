import time
from statistics import median

from lib.ep_handler import *
from lib.influxdb import *
from lib.denkovi_relay import *
from lib.configuration import *

import RPi.GPIO as GPIO
import board
from adafruit_ina219 import INA219, Gain


io = DenkoviRelay()

CELLS = 8

# INA219 I2C addresses: 0x40 ... 0x47
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

# Correction based on your measurements:
# 100 mV -> 76 mV
# 200 mV -> 176 mV
# 1000 mV -> 976 mV
#
# Set to 0.0 if you want the raw INA219 measurement.
BUS_VOLTAGE_OFFSET = 0.024  # V = 24 mV


# -------------------------------------------------------------------------
# GPIO
# -------------------------------------------------------------------------

BUFFER_RELAY_PIN = 19  # GPIO19 = physical pin 35

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUFFER_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)


# -------------------------------------------------------------------------
# INA219 initialisation
# -------------------------------------------------------------------------

i2c = board.I2C()

ina219_devices = {}

for address in INA219_ADDRESSES:
    try:
        ina = INA219(i2c, addr=address)

        # Maximum sensitivity for shunt measurement.
        # This does NOT affect the bus-voltage measurement.
        ina.gain = Gain.DIV_1_40MV

        ina219_devices[address] = ina

        print(f"INA219 found at 0x{address:02X}")

    except Exception as e:
        print(f"ERROR: INA219 at 0x{address:02X} could not be initialized: {e}")


# -------------------------------------------------------------------------
# INA219 voltage read function
# -------------------------------------------------------------------------

def read_ina219_voltage(address, samples=5):
    """
    Read the bus voltage from the INA219 at the specified I2C address.

    Returns:
        voltage in mV, or None if the measurement failed.
    """

    if address not in ina219_devices:
        print(f"INA219 0x{address:02X} is not available")
        return None

    ina219 = ina219_devices[address]

    readings = []

    for _ in range(samples):
        try:
            voltage = ina219.bus_voltage

            # Apply the measured 24 mV offset correction
            voltage += BUS_VOLTAGE_OFFSET

            # Convert V -> mV
            voltage_mv = voltage * 1000.0

            readings.append(voltage_mv)

        except Exception as e:
            print(
                f"INA219 read failed at 0x{address:02X}: {e}"
            )

        time.sleep(0.05)

    if not readings:
        return None

    return median(readings)


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

    ep_change_resistance(0)

    time.sleep(3)

    voltage_buffer = []

    try:

        for i in range(CELLS):

            # -------------------------------------------------------------
            # Connect buffer
            # -------------------------------------------------------------

            GPIO.output(BUFFER_RELAY_PIN, GPIO.HIGH)

            time.sleep(0.5)

            # Select cell using Denkovi relay
            io.relay_on(i + 1)

            time.sleep(0.1)

            # -------------------------------------------------------------
            # Select corresponding INA219
            #
            # Cell 1 -> 0x40
            # Cell 2 -> 0x41
            # ...
            # Cell 8 -> 0x47
            # -------------------------------------------------------------

            ina_address = INA219_ADDRESSES[i]

            buffer_voltage = read_ina219_voltage(
                ina_address,
                samples=5
            )

            if buffer_voltage is None:
                print(
                    f"[Cell {i + 1}] ERROR: "
                    f"Could not read INA219 at 0x{ina_address:02X}"
                )

                # Keep buffer length consistent
                voltage_buffer.append(0)

            else:
                print(
                    f"[Cell {i + 1}] "
                    f"INA219 0x{ina_address:02X} "
                    f"Buffer Voltage: {buffer_voltage:.1f} mV"
                )

                voltage_buffer.append(
                    int(round(buffer_voltage))
                )

            # -------------------------------------------------------------
            # Disconnect cell
            # -------------------------------------------------------------

            time.sleep(0.1)

            io.relay_off(i + 1)

            time.sleep(0.1)

            GPIO.output(BUFFER_RELAY_PIN, GPIO.LOW)

            time.sleep(1)

    finally:
        GPIO.cleanup()


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