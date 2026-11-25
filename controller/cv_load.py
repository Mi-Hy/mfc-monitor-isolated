
import time
import board
import busio
import adafruit_mcp4725

from hardware_control import pca9548_select, pca9548_disable


# ============================================================
# Configuratie
# ============================================================

cv_load = {
    "active": 1,
    "c1_voltage": 5.0,
    "c2_voltage": 5.0,
    "c3_voltage": 5.0,
    "c4_voltage": 5.0,
    "c5_voltage": 5.0,
    "c6_voltage": 5.0,
    "c7_voltage": 5.0,
    "c8_voltage": 5.0,
}

I2C_ADDRESS = 0x61
VREF = 5.45
INACTIVE_VOLTAGE = 5.0


# ============================================================
# I2C initialiseren
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)


# ============================================================
# DAC functie
# ============================================================

def set_voltage(dac, voltage):
    """
    Stel de uitgangsspanning van een MCP4725 in.
    Resolutie: 12 bit (0-4095).
    """

    voltage = max(0.0, min(voltage, VREF))
    value = int((voltage / VREF) * 4095)

    dac.raw_value = value

    return value


# ============================================================
# CV Load aansturen
# ============================================================

def update_cv_load(config=cv_load):

    active = bool(config.get("active", 0))

    print(f"\n[CV LOAD] Active: {active}")

    for channel in range(8):

        channel_name = f"c{channel + 1}_voltage"

        if active:
            voltage = float(config.get(channel_name, 0.3))
        else:
            voltage = INACTIVE_VOLTAGE

        try:
            # Selecteer PCA9548A kanaal
            pca9548_select(channel)

            # Initialiseer DAC op geselecteerd kanaal
            dac = adafruit_mcp4725.MCP4725(
                i2c,
                address=I2C_ADDRESS
            )

            # Stel DAC-spanning in
            value = set_voltage(dac, voltage)

            print(
                f"[CV LOAD] Channel {channel}: "
                f"{voltage:.3f} V (DAC: {value})"
            )

        except Exception as e:
            print(
                f"[CV LOAD] ERROR channel {channel}: {e}"
            )

    # Schakel alle PCA9548A kanalen uit
    try:
        pca9548_disable()
    except Exception as e:
        print(f"[CV LOAD] Multiplexer disable error: {e}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    try:
        update_cv_load()

        print("\n[CV LOAD] Update completed.")

    except KeyboardInterrupt:
        print("\n[CV LOAD] Script stopped.")

    finally:
        try:
            pca9548_disable()
        except Exception:
            pass
