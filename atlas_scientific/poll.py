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

def parse_sensor_data(read_output):
    """Parseert de ruwe dev.read() output naar een (type, waarde) tuple.

    Voorbeeld: 'Success pH 99 : 7.889' -> ('pH', 7.889)
    """
    try:
        # Verwijder 'Success ' aan het begin indien aanwezig
        clean_str = read_output.replace("Success ", "").strip()

        # Splits op de dubbele punt ':' -> ['pH 99', '7.889']
        sensor_info, value_str = clean_str.split(":")

        # Pak de sensornaam (eerste woord vóór het adres)
        sensor_type = sensor_info.strip().split()[0]
        value = float(value_str.strip())

        return sensor_type, value
    except (ValueError, IndexError):
        # Als de uitlezing mislukt (bijv. foutmelding of no-data)
        return None, None

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

    sensor_data = {}

    # 3. Lees de resultaten uit en print ze
    for dev in devices:
        print(f"[{dev.name} - Adres {dev.address}]: {dev.read()}")
        raw_output = dev.read()
        sensor_type, val = parse_sensor_data(raw_output)

        if sensor_type is not None:
            sensor_data[sensor_type] = val

    print(sensor_data)

    # 4. Sluit het script af
    sys.exit(0)


if __name__ == "__main__":
    read_all_once()

# def read_all_to_dict():
#     """Lest alle sensoren uit en geeft de resultaten terug als een dictionary."""
#     devices = get_devices()  # Veronderstelt dat get_devices() aanwezig is

#     if not devices:
#         print("Geen apparaten gevonden.")
#         sys.exit(1)

#     delay_time = max(dev.long_timeout for dev in devices)

#     # 1. Start metingen
#     for dev in devices:
#         dev.write("R")

#     time.sleep(delay_time)

#     # 2. Verzamel gegevens in een dictionary
#     sensor_data = {}

#     for dev in devices:
#         raw_output = dev.read()
#         print(dev.read())
#         sensor_type, val = parse_sensor_data(raw_output)

#         if sensor_type is not None:
#             sensor_data[sensor_type] = val

#     return sensor_data


# if __name__ == "__main__":
#     results = read_all_to_dict()

#     # Het resultaat is nu een schone dictionary:
#     print("Geparseerde gegevens:", results)
#     # Output: {'DO': 0.65, 'pH': 7.889, 'EC': 0.0, 'RTD': 26.794}

#     # Je kunt nu direct specifieke waarden opvragen:
#     if "pH" in results:
#         print(f"Huidige pH-waarde: {results['pH']}")

#     sys.exit(0)