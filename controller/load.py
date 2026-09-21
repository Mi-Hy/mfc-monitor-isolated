from lib.ep_handler import *
from lib.influxdb import *
from lib.tca9554 import TCA9554
from lib.configuration import *
import time

io = TCA9554()

# CELL_ARRAY = [0, 1, 2, 3]
CELL_ARRAY = [3]

#test

target_load = [30e3, 10e3, 5e3]#, 3e3, 1e3, 500]
target_load_index = [407, 461, 591]#, 643, 695, 708]

sample_interval = 10
target_load_duration = 600
start = time.monotonic()

if __name__ == "__main__":

    # Get config file
    config = retrieve_yaml_file()

    while(config['activity']['voltage'] == 1):
        #   Debug message
        print("[Load] ⏳ Waiting for voltage test to complete...")
        
        #   Wait 5 seconds before checking again
        time.sleep(5)

        #   Update config file to indicate voltage test is running
        config = retrieve_yaml_file()

    update_yaml_flag("activity", "load", 1)

    ep_change_resistance(0)

    time.sleep(3)

    voltage_buffer = []

    for cell_number in CELL_ARRAY:
        io.set_output(cell_number*2, 1)
        io.set_output(cell_number*2 + 1, 1)

        # Sweep through target load values
        for load_number in range(len(target_load)):
            
            while(get_ep_data()["pot_val"] != target_load_index[load_number]):
                ep_change_resistance(target_load_index[load_number])
                time.sleep(1.5)

            print(f"[Cell {cell_number}] Target Load successfully set: {target_load[load_number]} Ohms")

            start = time.monotonic()
            next_run = start
        
            while True:
                now = time.monotonic()
                if now - start >= target_load_duration:
                    time.sleep(sample_interval)
                    break

                print(f"[Cell {cell_number}] [{target_load_index[load_number]}] Running...")

                ep_data = get_ep_data()

                # Remove timestamp
                measurement_data = ep_data.copy()
                measurement_data.pop("timestamp", None)
                
                #   Send data to InfluxDB
                send_load_info(config, "[Load]", measurement_data, target_load[load_number], cell_number)
                
                # print(ep_data)

                next_run += sample_interval
                sleep_time = next_run - time.monotonic()

                if sleep_time > 0:
                    time.sleep(sleep_time)

        #   Change resistance back to 0 Ohms
        # ep_change_resistance(0)

        time.sleep(0.5)

        io.set_output(cell_number*2, 0)
        io.set_output(cell_number*2 + 1, 0)

        time.sleep(2)
    
    update_yaml_flag("activity", "load", 0)