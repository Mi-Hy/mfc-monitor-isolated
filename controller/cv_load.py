
import time
import board
import busio
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

VREF = 5.45
INACTIVE_VOLTAGE = 5.0
MCP4725_ADDRESS = 0x61


# ============================================================
# I2C initialiseren
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)


# ============================================================
# DAC functie
# ============================================================

# def set_voltage(dac, voltage):
#     """
#     Stel de uitgangsspanning van een MCP4725 in.
#     Resolutie: 12 bit (0-4095).
#     """

#     voltage = max(0.0, min(voltage, VREF))
#     value = int((voltage / VREF) * 4095)

#     dac.raw_value = value

#     return value


def set_voltage(bus, voltage):
    if not 0 <= voltage <= VREF:
        raise ValueError(f"Voltage must be between 0 and {VREF} V")

    # Omzetten naar 12-bit DAC-waarde
    value = int((voltage / VREF) * 4095)

    # MCP4725 Fast Mode Write
    data_high = (value >> 8) & 0x0F
    data_low = value & 0xFF

    bus.write_i2c_block_data(
        MCP4725_ADDRESS,
        data_high,
        [data_low]
    )

    print(f"DAC ingesteld: {voltage:.3f} V (raw={value})")

# ============================================================
# CV Load aansturen
# ============================================================

def update_cv_load(config=cv_load):
    with SMBus(I2C_BUS) as bus:

        # Check if the constant voltage load is activated
        active = bool(config.get("active", 0))
        print(f"\n[CV LOAD] Active: {active}")

        # Sweep over all 8 channels
        for channel in range(8):

            # Convert to channel name
            channel_name = f"c{channel + 1}_voltage"

            # Determine the voltage to set based on the active status
            if active:
                voltage = float(config.get(channel_name, 0.3))
            else:
                voltage = INACTIVE_VOLTAGE

            try:
                # Select the PCA9548A channel
                pca9548_select(bus, channel)

                # time.sleep(0.2)  # Wait a bit for stability

                # Set the voltage on the DAC for the selected channel
                value = set_voltage(bus, voltage)

                time.sleep(0.01) 

                # Disable all channels after setting the voltage
                pca9548_disable(bus)

                print(
                    f"[CV LOAD] Channel {channel}: "
                    f"{voltage:.3f} V (DAC: {value})"
                )

            except Exception as e:
                print(
                    f"[CV LOAD] ERROR channel {channel}: {e}"
                )



# def update_cv_load(config=cv_load):

#     active = bool(config.get("active", 0))

#     print(f"\n[CV LOAD] Active: {active}")

#     for channel in range(8):

#         channel_name = f"c{channel + 1}_voltage"

#         if active:
#             voltage = float(config.get(channel_name, 0.3))
#         else:
#             voltage = INACTIVE_VOLTAGE

#         try:
#             # Selecteer PCA9548A kanaal
#             pca9548_select(channel)

#             time.sleep(0.2)  # Wacht even voor stabiliteit

#             # Initialiseer DAC op geselecteerd kanaal
#             # dac = adafruit_mcp4725.MCP4725(
#             #     i2c,
#             #     address=I2C_ADDRESS
#             # )

#             # Stel DAC-spanning in
#             value = set_voltage(MCP4725_ADDRESS, voltage)

#             time.sleep(0.2)  # Wacht even voor stabiliteit

#             print(
#                 f"[CV LOAD] Channel {channel}: "
#                 f"{voltage:.3f} V (DAC: {value})"
#             )

#             pca9548_disable()

#             time.sleep(0.2)  # Wacht even voor stabiliteit

#         except Exception as e:
#             print(
#                 f"[CV LOAD] ERROR channel {channel}: {e}"
#             )

#     # Schakel alle PCA9548A kanalen uit
#     try:
#         pca9548_disable()
#     except Exception as e:
#         print(f"[CV LOAD] Multiplexer disable error: {e}")


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
