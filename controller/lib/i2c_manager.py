import RPi.GPIO as GPIO
from smbus2 import SMBus

# GPIO configuratie
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(4, GPIO.OUT, initial=GPIO.LOW)

# PCA9548A configuratie
I2C_BUS = 1
PCA9548_ADDRESS = 0x70

# GPIO4
def gpio4_high():
    # GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.HIGH)

def gpio4_low():
    # GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.LOW)


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