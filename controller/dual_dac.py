
import time
import board
import busio
import adafruit_mcp4725

# I2C initialiseren
i2c = busio.I2C(board.SCL, board.SDA)

# Beide MCP4725 DAC's initialiseren
dac_1 = adafruit_mcp4725.MCP4725(i2c, address=0x60)
dac_2 = adafruit_mcp4725.MCP4725(i2c, address=0x61)

# Referentiespanning (VDD van de DAC)
VREF = 5.45

def set_voltage(dac, voltage):
    """
    Stel de uitgangsspanning van een MCP4725 in.
    Resolutie: 12 bit (0-4095).
    """
    voltage = max(0.0, min(voltage, VREF))

    value = int((voltage / VREF) * 4095)

    dac.raw_value = value

    print(f"Spanning ingesteld: {voltage:.3f} V "
          f"(DAC value: {value})")


try:
    # DAC op adres 0x60: 1.0 V
    # set_voltage(dac_1, 0.25)

    # DAC op adres 0x61: 3.0 V
    set_voltage(dac_2, 0.3)

    print("Beide DAC-uitgangen zijn ingesteld.")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nScript gestopt.")

