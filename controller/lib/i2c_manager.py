import RPi.GPIO as GPIO
from smbus2 import SMBus

# GPIO configuratie
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# PCA9548A configuratie
I2C_BUS = 1
PCA9548_ADDRESS = 0x70

# GPIO4
def gpio4_high():
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.HIGH)

def gpio4_low():
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.LOW)


# PCA9548A functies
def pca9548_select(channel):

    pca9548_disable()

    """Selecteer een kanaal van de PCA9548A (0-7)."""
    if not 0 <= channel <= 7:
        raise ValueError("Channel must be between 0 and 7")

    with SMBus(I2C_BUS) as bus:
        bus.write_byte(PCA9548_ADDRESS, 1 << channel)


def pca9548_disable():
    """Schakel alle PCA9548A kanalen uit."""
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(PCA9548_ADDRESS, 0x00)


def pca9548_enable_all():
    """Schakel alle PCA9548A kanalen in."""
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(PCA9548_ADDRESS, 0xFF)

def connect_water_quality_sensors():
    """Connect water quality sensors to the I2C bus."""        
    # Disable PCA9548 multiplexer to avoid I2C conflicts with water quality sensors
    pca9548_disable()

    # Connect water quality sensors to the I2C bus
    gpio4_high()

def disconnect_water_quality_sensors():
    """Disconnect water quality sensors from the I2C bus."""
    # Disconnect water quality sensors from the I2C bus
    gpio4_low()