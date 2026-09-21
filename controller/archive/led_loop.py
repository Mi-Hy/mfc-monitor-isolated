from lib.ep_handler import *
from lib.influxdb import *
from lib.tca9554 import TCA9554
from lib.configuration import *

io = TCA9554()

CELLS = 8

value_mapper = {0: 3, 1: 2, 2: 1, 3: 0, 4: 7, 5: 6, 6: 5, 7: 4}

if __name__ == "__main__":


    while True:

        for i in range(CELLS):
            io.set_output(value_mapper.get(i, i), 1)

            time.sleep(1)

            io.set_output(value_mapper.get(i, i), 0)

            time.sleep(1)
    

