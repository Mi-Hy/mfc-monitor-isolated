from smbus2 import SMBus

REG_INPUT = 0x00
REG_OUTPUT = 0x01
REG_POLARITY = 0x02
REG_CONFIG = 0x03


class TCA9554:

    def __init__(self, bus=1, address=0x38):
        self.bus = SMBus(bus)
        self.address = address

        # P0-P7 standaard output
        self.bus.write_byte_data(self.address, REG_CONFIG, 0x00)

        # alle outputs laag
        self.output_state = 0x00
        self.bus.write_byte_data(self.address, REG_OUTPUT, self.output_state)

    def select_output(self, pin):
        """
        Zet enkel de gekozen pin HIGH, alle andere LOW
        pin = 0..7
        """
        if pin < 0 or pin > 7:
            raise ValueError("Pin must be between 0 and 7")

        self.output_state = 1 << pin
        self.bus.write_byte_data(self.address, REG_OUTPUT, self.output_state)

    def set_output(self, pin, value):
        """
        Zet een individuele pin HIGH of LOW
        """
        if value:
            self.output_state |= (1 << pin)
        else:
            self.output_state &= ~(1 << pin)

        self.bus.write_byte_data(self.address, REG_OUTPUT, self.output_state)

    def read_inputs(self):
        return self.bus.read_byte_data(self.address, REG_INPUT)