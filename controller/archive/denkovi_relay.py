from pyftdi.ftdi import Ftdi


class DenkoviRelay:
    def __init__(self, vendor=0x0403, product=0x6001):
        self.ftdi = Ftdi()
        self.ftdi.open(vendor=vendor, product=product)

        # Alle 8 pinnen als uitgang
        self.ftdi.set_bitmode(0xFF, Ftdi.BitMode.BITBANG)

        self.state = 0x00
        self._write()

    def _write(self):
        self.ftdi.write_data(bytes([self.state]))

    def relay_on(self, relay):
        """Relay 1-8 aan"""
        if not 1 <= relay <= 8:
            raise ValueError("Relay must be between 1 and 8")

        self.state |= (1 << (relay - 1))
        self._write()

    def relay_off(self, relay):
        """Relay 1-8 uit"""
        if not 1 <= relay <= 8:
            raise ValueError("Relay must be between 1 and 8")

        self.state &= ~(1 << (relay - 1))
        self._write()

    def relay_toggle(self, relay):
        """Relay 1-8 toggelen"""
        if not 1 <= relay <= 8:
            raise ValueError("Relay must be between 1 and 8")

        self.state ^= (1 << (relay - 1))
        self._write()

    def all_on(self):
        self.state = 0xFF
        self._write()

    def all_off(self):
        self.state = 0x00
        self._write()

    def set_state(self, state):
        """State = 0-255"""
        self.state = state & 0xFF
        self._write()

    def get_state(self):
        return self.state

    def close(self):
        self.all_off()
        self.ftdi.close()