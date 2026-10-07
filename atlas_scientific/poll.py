#!/usr/bin/python

import sys
import time
from AtlasI2C import AtlasI2C


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


def read_all_once():
    """Voert één poll uit voor alle aangesloten sensoren, print het resultaat en sluit af."""
    devices = get_devices()

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

    # 3. Lees de resultaten uit en print ze
    for dev in devices:
        print(f"[{dev.name} - Adres {dev.address}]: {dev.read()}")

    # 4. Sluit het script af
    sys.exit(0)


if __name__ == "__main__":
    read_all_once()