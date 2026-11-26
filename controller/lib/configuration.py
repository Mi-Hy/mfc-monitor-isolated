import yaml
import os
from filelock import FileLock

# CONFIG_PATH = "config.yaml"
# CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
home_dir = os.path.expanduser("~")

# for testing WINDOWS
home_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
print(home_dir)

CONFIG_PATH = home_dir + "/config.yaml"
LOCK_PATH = CONFIG_PATH + ".lock"

def retrieve_yaml_file():
    config = {}
    try:
        with FileLock(LOCK_PATH):
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as file:
                    config = yaml.safe_load(file) or {}
    except Exception as e:
        print(f"⚠️ Error reading YAML file: {e}")

    return config

#   YAML functions
def update_yaml_flag(TAGlvl1, TAGlvl2, value):
    try:
        with FileLock(LOCK_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f) or {}

            # Check of de eerste en tweede tag bestaan
            if TAGlvl1 not in config or TAGlvl2 not in config[TAGlvl1]:
                raise KeyError(f"'{TAGlvl1}' or '{TAGlvl2}' not found in config")

            # Pas de waarde aan
            config[TAGlvl1][TAGlvl2] = value

            # Schrijf het bestand terug
            with open(CONFIG_PATH, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)

    except Exception as e:
        print(f"⚠️ Failed to update config: {e}")


#   Function to check if any other script is running
def get_activity_status():
    try:
        config = retrieve_yaml_file()

        # Get the 'activity'-section from the config, defaulting to an empty dict if not present
        activity = (config or {}).get("activity") or {}

        for key in activity:
            if activity[key] == 1:
                return 1

        return 0
    except Exception as e:
        print(f"⚠️ Error occurred: {e}")
        return 1


def get_sensor_req_status():
    try:
        config = retrieve_yaml_file()
        requests = (config or {}).get("sensor_requests") or {}

        for key, value in requests.items():
            if "req" in key and value == 1:
                return 1

        return 0
    except Exception as e:
        print(f"⚠️ Error occurred: {e}")
        return 0