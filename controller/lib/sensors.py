#!/usr/bin/python

import sys
import time
from lib.AtlasI2C import AtlasI2C
import re
from lib.configuration import *


def get_devices():
    """Detecteert automatisch alle geldige Atlas EZO I2C-apparaten."""
    device = AtlasI2C()
    device_address_list = device.list_i2c_devices()
    device_list = []

    for addr in device_address_list:
        device.set_i2c_address(addr)
        try:
            response = device.query("I")
            moduletype = response.split(",")[1]
            name = device.query("name,?").split(",")[1]
            device_list.append(
                AtlasI2C(address=addr, moduletype=moduletype, name=name)
            )
        except (IndexError, IOError):
            continue

    return device_list


def parse_sensor_data(read_output):
    """Haalt de sensornaam en de daadwerkelijke meetwaarde uit de output,

    waarbij het adresnummer (bijv. 97, 99) altijd wordt overgeslagen.
    """
    # 1. Zoek de bekende sensornaam (DO, pH, EC, RTD)
    type_match = re.search(r"\b(DO|pH|EC|RTD)\b", read_output, re.IGNORECASE)

    # 2. Zoek ALLE getallen (integers en floats, inclusief negatieve getallen)
    numbers = re.findall(r"-?\d+(?:\.\d+)?", read_output)

    if type_match and numbers:
        sensor_type = type_match.group(1).upper()
        # De meetwaarde staat ALTIJD als laatste getal in de string
        value = float(numbers[-1])
        return sensor_type, value

    return None, None

def read_all_once():
    """Voert één poll uit voor alle aangesloten sensoren, print het resultaat en sluit af."""
    devices = get_devices()

    # print([dev.address for dev in devices])
    
    if not devices:
        print("Geen Atlas Scientific EZO I2C-apparaten gevonden.")
        sys.exit(1)

    # Bepaal de langste vereiste wachttijd van de aangesloten apparaten
    delay_time = max(dev.long_timeout for dev in devices)

    # 1. Stuur het 'R' (Read) commando naar alle apparaten
    for dev in devices:
        dev.write("R")

    # 2. Wacht tot de sensoren de meting voltooid hebben
    time.sleep(delay_time)

    sensor_data = {}

    # 3. Lees de resultaten uit en print ze
    for dev in devices:
        raw_output = dev.read()
        # print(f"[{dev.name} - Adres {dev.address}]: {raw_output}")
        sensor_type, val = parse_sensor_data(raw_output)
        # print(sensor_type,val)

        if sensor_type is not None:
            sensor_data[sensor_type] = val

    # print(sensor_data)

    return sensor_data

    # 4. Sluit het script af
    # sys.exit(0)



def read_all_once_temp_compensated():
    """Meet de temperatuur via RTD, stel temperatuurcompensatie in
    voor de andere sensoren en lees alle sensoren uit.
    """
    devices = get_devices()

    if not devices:
        print("Geen Atlas Scientific EZO I2C-apparaten gevonden.")
        sys.exit(1)

    # Zoek de RTD-sensor
    rtd_devices = [dev.address for dev in devices]
    # print(rtd_devices)

    rtd_index = rtd_devices.index(102) if 102 in rtd_devices else -1

    if rtd_index == -1:
        print("Geen RTD-sensor gevonden.")
        sys.exit(1)

    rtd = devices[rtd_index]

    # 1. Vraag de temperatuur op bij de RTD-sensor
    rtd.write("R")
    time.sleep(rtd.long_timeout)

    raw_output = rtd.read()
    sensor_type, temperature = parse_sensor_data(raw_output)

    if sensor_type != "RTD" or temperature is None:
        print(f"Kon RTD-temperatuur niet uitlezen: {raw_output}")
        return {}

    print(f"RTD-temperatuur: {temperature} °C")

    # 2. Stel temperatuurcompensatie in voor de andere sensoren
    for dev in devices:
        if dev is not rtd:
            dev.write(f"RT,{temperature}")

    # 3. Wacht tot de commando's verwerkt zijn
    time.sleep(0.3)

    # 4. Vraag alle sensoren opnieuw uit
    for dev in devices:
        dev.write("R")

    # Wacht tot alle metingen voltooid zijn
    delay_time = max(dev.long_timeout for dev in devices)
    time.sleep(delay_time)

    # 5. Lees alle resultaten uit
    sensor_data = {"RTD": temperature}

    for dev in devices:
        if dev is rtd:
            continue

        raw_output = dev.read()
        sensor_type, val = parse_sensor_data(raw_output)

        if sensor_type is not None:
            sensor_data[sensor_type] = val

    return sensor_data


def find_device(device_number):
    devices = get_devices()

    if not devices:
        print("No Atlas Scientific EZO I2C-devices found!")
        sys.exit(1)

    # Zoek de PH-sensor
    devices_addresses = [dev.address for dev in devices]
    device_index = devices_addresses.index(device_number) if device_number in devices_addresses else -1

    if device_index == -1:
        print("Geen PH-sensor gevonden.")
        sys.exit(1)

    return devices[device_index]


# def ph_cal():
#     ph_device = find_device(99)
#     ph_device.write(f"Cal,?")
#     time.sleep(ph_device.long_timeout)

#     raw_output = ph_device.read()

#     # value = raw_output.split(",")[1]
#     value = int(raw_output.split(",")[1].rstrip("\0"))
#     update_yaml_flag("sensor_responses", "ph_cal_rsp_status", value)

# def ph_cal_clear():
#     ph_device = find_device(99)
#     ph_device.write(f"Cal,clear")
#     time.sleep(ph_device.long_timeout)
#     return ph_device.read()

# def ph_cal_mid():
#     ph_device = find_device(99)
#     ph_device.write(f"Cal,mid,7.00")
#     time.sleep(ph_device.long_timeout)
#     return ph_device.read()   

# def ph_cal_low():
#     ph_device = find_device(99)
#     ph_device.write(f"Cal,low,4.00")
#     time.sleep(ph_device.long_timeout)
#     return ph_device.read()

# def ph_cal_high():
#     ph_device = find_device(99)
#     ph_device.write(f"Cal,high,10.00")
#     time.sleep(ph_device.long_timeout)
#     return ph_device.read()


def ph_cal():
    print("[Sensors][PH] Checking calibration status...")
    ph_device = find_device(99)
    ph_device.write("Cal,?")
    time.sleep(ph_device.long_timeout)

    raw_output = ph_device.read()
    value = int(raw_output.split(",")[1].rstrip("\0"))

    print(f"[Sensors][PH] Calibration status: {value}")
    update_yaml_flag("sensor_responses", "ph_cal_rsp_status", value)


def ph_cal_clear():
    print("[Sensors][PH] Clearing calibration...")
    ph_device = find_device(99)
    ph_device.write("Cal,clear")
    time.sleep(ph_device.long_timeout)

    response = ph_device.read()
    print(f"[Sensors][PH] Clear calibration response: {response}")
    return response


def ph_cal_mid():
    print("[Sensors][PH] Starting mid-point calibration (pH 7.00)...")
    ph_device = find_device(99)
    ph_device.write("Cal,mid,7.00")
    time.sleep(ph_device.long_timeout)

    response = ph_device.read()
    print(f"[Sensors][PH] Mid-point calibration response: {response}")
    return response


def ph_cal_low():
    print("[Sensors][PH] Starting low-point calibration (pH 4.00)...")
    ph_device = find_device(99)
    ph_device.write("Cal,low,4.00")
    time.sleep(ph_device.long_timeout)

    response = ph_device.read()
    print(f"[Sensors][PH] Low-point calibration response: {response}")
    return response


def ph_cal_high():
    print("[Sensors][PH] Starting high-point calibration (pH 10.00)...")
    ph_device = find_device(99)
    ph_device.write("Cal,high,10.00")
    time.sleep(ph_device.long_timeout)

    response = ph_device.read()
    print(f"[Sensors][PH] High-point calibration response: {response}")
    return response

if __name__ == "__main__":
    print(read_all_once())
    print(read_all_once_temp_compensated())
