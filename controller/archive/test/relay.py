from pyftdi.ftdi import Ftdi
import time

ftdi = Ftdi()
ftdi.open(vendor=0x0403, product=0x6001)

# Alle 8 pinnen als uitgang
ftdi.set_bitmode(0xFF, Ftdi.BitMode.BITBANG)

# Relay 1 aan
ftdi.write_data(b'\xFF')

time.sleep(2)

# Alles uit
ftdi.write_data(b'\x00')

ftdi.close()