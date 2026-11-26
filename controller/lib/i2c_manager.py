from smbus2 import SMBus
from lib.gpio import gpio4_high, gpio4_low

# PCA9548A configuratie
I2C_BUS = 1
PCA9548_ADDRESS = 0x70

def pca9548_select(bus, channel):
    if not 0 <= channel <= 7:
        raise ValueError("Channel must be between 0 and 7")

    # Alle kanalen uitschakelen
    bus.write_byte(PCA9548_ADDRESS, 0x00)

    # Enkel het gewenste kanaal activeren
    bus.write_byte(PCA9548_ADDRESS, 1 << channel)

    # Controleer de ingestelde kanaalstatus
    value = bus.read_byte(PCA9548_ADDRESS)

    if value != (1 << channel):
        raise RuntimeError(
            f"PCA9548A channel selection failed: 0x{value:02X}"
        )

def pca9548_disable(bus):
    """Schakel alle PCA9548A kanalen uit."""
    bus.write_byte(PCA9548_ADDRESS, 0x00)


def pca9548_enable_all(bus):
    """Schakel alle PCA9548A kanalen in."""
    bus.write_byte(PCA9548_ADDRESS, 0xFF)

def connect_water_quality_sensors(bus):
    """Connect water quality sensors to the I2C bus."""        
    # Disable PCA9548 multiplexer to avoid I2C conflicts with water quality sensors
    pca9548_disable(bus)

    # Connect water quality sensors to the I2C bus
    gpio4_high()

def disconnect_water_quality_sensors():
    """Disconnect water quality sensors from the I2C bus."""
    # Disconnect water quality sensors from the I2C bus
    gpio4_low()