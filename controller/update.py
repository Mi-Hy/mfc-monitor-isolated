import time
from statistics import median

import board
from adafruit_ina219 import INA219, Gain

from lib.influxdb import *
from lib.denkovi_relay import *
from lib.configuration import *

import RPi.GPIO as GPIO

from lib.ina226 import INA226

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

INA226_ADDRESSES = [
    0x44,
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
# Initialize INA-sensors
# -------------------------------------------------------------------------

# def initialize_ina_devices(sensor_type):

#     ina_devices = []

#     if sensor_type == "INA219":

#         for address in INA_ADDRESSES:

#             ina219 = INA219(i2c, addr=address)

#             # Maximale gevoeligheid:
#             # ±40 mV shunt-voltage range
#             ina219.gain = Gain.DIV_1_40MV

#             # Shuntweerstand = 100 mΩ
#             ina219.shunt_resistance = 0.1

#             ina_devices.append(ina219)

#             print(f"INA219 initialized at 0x{address:02X}")

#             return ina_devices

#     if sensor_type == "INA226":

#         for address in INA_ADDRESSES:a

#             # INA226 is not implemented yet
#             print(f"INA226 is not implemented yet at 0x{address:02X}")

#             return ina_devices




def initialize_ina_devices(sensor_type, cells, ina_addresses):

    ina_devices = []

    for cell in range(cells):

        if sensor_type == "INA219":

            ina = INA219(i2c, addr=ina_addresses[cell])

            ina.gain = Gain.DIV_1_40MV
            ina.shunt_resistance = 0.1

        elif sensor_type == "INA226":

            ina = INA226(
                address=ina_addresses[cell],
                bus=1,
                shunt_resistance=0.1,
                max_expected_current=0.8
            )

            #debug
            print(ina.diagnostics())
            raw = ina._read_register(0x01)
            print(f"Raw shunt register: 0x{raw:04X}")
            print(f"Shunt voltage: {raw * 2.5e-6 * 1000:.3f} mV")

        else:
            raise ValueError(
                f"Unsupported sensor type: {sensor_type}"
            )

        ina_devices.append(ina)

        print(
            f"{sensor_type} initialized at "
            f"0x{ina_addresses[cell]:02X}"
        )

    return ina_devices



# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

if __name__ == "__main__":

    # Get config file
    config = retrieve_yaml_file()

    # Get sensor type from config file
    sensor_type = config.get("fixed_configurations", {}).get("sensor_type", "INA219")

    # Get number of cells from config file
    cells = config.get("fixed_configurations", {}).get("cells", 1)

    # Print sensor type and number of cells
    print(f"Sensor type: {sensor_type}")
    print(f"Number of cells: {cells}")

    # Check if load test is running
    while config['activity']['load'] == 1:

        print("[Voltage] ⏳ Waiting for load test to complete...")

        time.sleep(5)

        config = retrieve_yaml_file()

    # Update activity flag in config.yaml to indicate that cell measurement is in progress
    update_yaml_flag("activity", "voltage", 1)

    voltage_buffer = []
    current_buffer = []

    ina_addresses = INA219_ADDRESSES if sensor_type == "INA219" else INA226_ADDRESSES

    ina_devices = initialize_ina_devices(sensor_type, cells, ina_addresses)


    for i in range(cells):


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

        # if sensor_type == "INA219":

        #     ina219 = ina_devices[i]

        #     buffer_voltages = []
        #     buffer_currents = []

        #     for _ in range(5):

        #         try:
        #             # Voltage
        #             voltage = ina219.bus_voltage
        #             voltage_mv = voltage * 1000
        #             buffer_voltages.append(voltage_mv)

        #             # Current
        #             current = ina219.current
        #             buffer_currents.append(current)

        #         except Exception as e:
        #             print(
        #                 f"[Cell {i + 1}] "
        #                 f"INA219 read error: {e}"
        #             )

        #         time.sleep(0.05)

        # if sensor_type == "INA226":

        #     ina226 = ina_devices[i]
            
        #     # INA226 is not implemented yet
        #     print(
        #         f"[Cell {i + 1}] "
        #         f"INA226 is not implemented yet"
        #     )

        #     buffer_voltages = []
        #     buffer_currents = []



        buffer_voltages = []
        buffer_currents = []

        for _ in range(5):

            try:

                # Voltage in V -> mV
                voltage = ina_devices[i].bus_voltage
                voltage_mv = voltage * 1000

                # Current
                current = ina_devices[i].current

                if sensor_type == "INA219":
                    # INA219 library returns mA
                    current_ma = current

                elif sensor_type == "INA226":
                    # INA226 driver returns A -> mA
                    current_ma = current * 1000

                buffer_voltages.append(voltage_mv)
                buffer_currents.append(current_ma)

            except Exception as e:

                print(
                    f"[Cell {i + 1}] "
                    f"{sensor_type} read error: {e}"
                )

            time.sleep(0.05)


        # -------------------------------------------------------------
        # Median of the 5 voltage measurements
        # -------------------------------------------------------------

        if buffer_voltages:

            buffer_voltage_median = median(buffer_voltages)

            print(
                f"[Cell {i + 1}] "
                f"{sensor_type} 0x{ina_addresses[i]:02X} "
                f"Buffer Voltage: "
                f"{buffer_voltage_median:.1f} mV"
            )

            voltage_buffer.append(
                int(round(buffer_voltage_median))
            )

        else:

            print(
                f"[Cell {i + 1}] "
                f"Could not read {sensor_type} voltage"
            )

            voltage_buffer.append(0)


        # -------------------------------------------------------------
        # Median of the 5 current measurements
        # -------------------------------------------------------------

        if buffer_currents:

            buffer_current_median = median(buffer_currents)

            print(
                f"[Cell {i + 1}] "
                f"{sensor_type} 0x{ina_addresses[i]:02X} "
                f"Buffer Current: "
                f"{buffer_current_median:.2f} mA"
            )

            current_buffer.append(
                round(buffer_current_median, 2)
            )

        else:

            print(
                f"[Cell {i + 1}] "
                f"Could not read {sensor_type} current"
            )

            current_buffer.append(0)

        # buffer_voltages = []

        # for _ in range(5):

        #     try:

        #         voltage = ina219.bus_voltage

        #         # Convert V -> mV
        #         voltage_mv = voltage * 1000

        #         buffer_voltages.append(voltage_mv)

        #     except Exception as e:

        #         print(
        #             f"[Cell {i + 1}] "
        #             f"INA219 read error: {e}"
        #         )

        #     time.sleep(0.05)

        # # -------------------------------------------------------------
        # # Median of the 5 measurements
        # # -------------------------------------------------------------

        # if buffer_voltages:

        #     buffer_voltage_median = median(buffer_voltages)

        #     print(
        #         f"[Cell {i + 1}] "
        #         f"INA219 0x{INA219_ADDRESSES[i]:02X} "
        #         f"Buffer Voltage: "
        #         f"{buffer_voltage_median:.1f} mV"
        #     )

        #     voltage_buffer.append(
        #         int(round(buffer_voltage_median))
        #     )

        # else:

        #     print(
        #         f"[Cell {i + 1}] "
        #         f"Could not read INA219"
        #     )

        #     voltage_buffer.append(0)




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

print("CELLS:", cells)
print("voltage_buffer:", voltage_buffer)
print("length:", len(voltage_buffer))


try:

    # if device_mode == "series":

    #     voltage_data = {}
    #     current_data = {}

    #     previous = 0

    #     for i in range(CELLS):

    #         voltage_data[f"cell_{i}"] = (
    #             voltage_buffer[i] - previous
    #         )

    #         previous = voltage_buffer[i]

    # else:

    voltage_data = {
        f"cell_{i}": voltage_buffer[i]
        for i in range(cells)
    }

    current_data = {
        f"cell_{i}": current_buffer[i]
        for i in range(cells)
    }

except IndexError as e:

    print(f"Voltage buffer index error: {e}")

    voltage_data = {}
    current_data = {}


# -------------------------------------------------------------------------
# Send voltage information
# -------------------------------------------------------------------------

# print(voltage_data)
# print(current_data)

if voltage_data:

    send_power_sensors_info(
        config,
        "[Power Sensors]",
        voltage_data,
        current_data
    )


update_yaml_flag("activity", "voltage", 0)
