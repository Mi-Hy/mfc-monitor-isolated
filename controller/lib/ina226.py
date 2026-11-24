
from smbus2 import SMBus


class INA226:

    REG_CONFIG = 0x00
    REG_BUS_VOLTAGE = 0x02
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05

    def __init__(
        self,
        address,
        bus=1,
        shunt_resistance=0.1,
        max_expected_current=0.8
    ):

        self.address = address
        self.bus = SMBus(bus)
        self.shunt_resistance = shunt_resistance

        # Current LSB in A/bit
        self.current_lsb = max_expected_current / 32768.0

        # INA226 calibration register
        calibration = int(
            0.00512 /
            (self.current_lsb * self.shunt_resistance)
        )

        self.calibration = calibration

        # Configure INA226:
        # Continuous shunt + bus voltage measurements
        # 1.1 ms conversion time
        # No internal averaging (external median is used)
        self._write_register(self.REG_CONFIG, 0x4127)

        self._write_register(
            self.REG_CALIBRATION,
            self.calibration
        )

    def _read_register(self, register):

        value = self.bus.read_word_data(
            self.address,
            register
        )

        # INA226 uses big-endian register values
        return ((value & 0xFF) << 8) | (value >> 8)

    def _write_register(self, register, value):

        value = int(value)

        swapped = (
            ((value & 0xFF) << 8) |
            ((value >> 8) & 0xFF)
        )

        self.bus.write_word_data(
            self.address,
            register,
            swapped
        )

    @property
    def bus_voltage(self):

        raw = self._read_register(self.REG_BUS_VOLTAGE)

        # 1.25 mV per bit
        return raw * 0.00125

    @property
    def current(self):

        raw = self._read_register(self.REG_CURRENT)

        # Convert unsigned register to signed 16-bit
        if raw & 0x8000:
            raw -= 65536

        return raw * self.current_lsb

    def close(self):

        self.bus.close()
