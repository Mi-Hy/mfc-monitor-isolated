
import time
import board
import busio
import adafruit_mcp4725

from lib.i2c_manager import *


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

        # try:
        #     # Selecteer PCA9548A kanaal
        #     pca9548_select(channel)

        #     time.sleep(0.2)  # Wacht even voor stabiliteit

        #     # Initialiseer DAC op geselecteerd kanaal
        #     dac = adafruit_mcp4725.MCP4725(
        #         i2c,
        #         address=I2C_ADDRESS
        #     )

        #     # Stel DAC-spanning in
        #     value = set_voltage(dac, voltage)

        #     time.sleep(0.2)  # Wacht even voor stabiliteit

        #     print(
        #         f"[CV LOAD] Channel {channel}: "
        #         f"{voltage:.3f} V (DAC: {value})"
        #     )

        #     pca9548_disable()

        #     time.sleep(0.2)  # Wacht even voor stabiliteit

        # except Exception as e:
        #     print(
        #         f"[CV LOAD] ERROR channel {channel}: {e}"
        #     )


        try:
            # Selecteer PCA9548A kanaal
            pca9548_select(channel)

            time.sleep(0.2)

            # Detecteer DAC op I2C-adres 0x61
            try:
                while not i2c.try_lock():
                    time.sleep(0.01)

                found = I2C_ADDRESS in i2c.scan()

            finally:
                i2c.unlock()

            if not found:
                print(
                    f"[CV LOAD] Channel {channel}: "
                    f"I2C address 0x{I2C_ADDRESS:02X} NOT FOUND"
                )
                continue

            print(
                f"[CV LOAD] Channel {channel}: "
                f"I2C address 0x{I2C_ADDRESS:02X} FOUND"
            )

            time.sleep(0.2)

            # Initialiseer DAC op geselecteerd kanaal
            dac = adafruit_mcp4725.MCP4725(
                i2c,
                address=I2C_ADDRESS
            )

            # Stel DAC-spanning in
            value = set_voltage(dac, voltage)

            time.sleep(0.2)

            print(
                f"[CV LOAD] Channel {channel}: "
                f"{voltage:.3f} V (DAC: {value})"
            )

        except Exception as e:
            print(f"[CV LOAD] ERROR channel {channel}: {e}")

        finally:
            try:
                pca9548_disable()
                time.sleep(0.2)
            except Exception as e:
                print(f"[CV LOAD] Multiplexer disable error: {e}")

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
