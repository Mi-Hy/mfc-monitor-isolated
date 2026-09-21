from flask import Flask, session, render_template, request, jsonify, Response, redirect, url_for
# from scipy import io
from werkzeug.security import check_password_hash
import yaml
import os
from filelock import FileLock
import sys
from pathlib import Path
from functools import wraps

PC_DEBUG = True


BASE_DIR = Path(__file__).resolve().parent
LIB_DIR = (BASE_DIR / "..").resolve()

sys.path.append(str(LIB_DIR))

# exit()
from lib.configuration import *
from lib.socket_helper import *

# Set username and password
USERNAME = 'admin'
PASSWORD_HASH = "scrypt:32768:8:1$J9y6LUQ1tUPuZY5D$82c25112902c25477c1dc22f1be5ab3d5bd61b7f0578b92555eb0a91b0160c5f7337fa52dc08ad14be5bacbab5928855b25ebc89d359389d786360c1d0d18ff2"

app = Flask(__name__)
app.secret_key = '3c6d3b49babfc5e2fdf06dc410e84f90'

# PC SETTING FOR DEVELOPMENT *** TODO COMMENT OUT
if PC_DEBUG:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    LOCK_PATH = CONFIG_PATH + ".lock"
else:
# *** RPI SETTING *** TODO UNCOMMENT
    home_dir = os.path.expanduser("~")
    CONFIG_PATH = home_dir + "/config.yaml"
    LOCK_PATH = CONFIG_PATH + ".lock"

def check_auth(username, password):
    """Check if the provided username and password are correct"""
    return username == USERNAME and check_password_hash(PASSWORD_HASH, password)

def authenticate():
    """Send a 401 response to trigger basic auth"""
    response = Response(
        'Access denied.\n'
        'You must provide valid credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )
    # Voeg headers toe om caching te voorkomen
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization

        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()

        return f(*args, **kwargs)

    return decorated

@app.route('/')
@requires_auth
def index():
    config = retrieve_yaml_file()
    print(config)

    return render_template('index2.html', config=config)

@app.route('/save_config', methods=['POST'])
@requires_auth
def save_config():
    data = request.json  # De nieuwe data van de POST request
    print(data)

    try:
        # Lees de bestaande configuratie uit het YAML-bestand
        try:
            with FileLock(LOCK_PATH):
                with open(CONFIG_PATH, 'r') as file:
                    current_config = yaml.safe_load(file) or {}
        except FileNotFoundError:
            current_config = {}

        # Gebruik de deep_update-functie i.p.v. .update()
        deep_update(current_config, data)

        # Schrijf de gecombineerde configuratie terug naar het bestand
        with FileLock(LOCK_PATH):
            with open(CONFIG_PATH, 'w') as file:
                yaml.dump(current_config, file)

        return jsonify({"status": "success", "message": "Config saved."})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def deep_update(source, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(source.get(key), dict):
            deep_update(source[key], value)
        else:
            source[key] = value

def save_config(config):
    with FileLock(LOCK_PATH):
        with open(CONFIG_PATH, 'w') as file:
            yaml.dump(config, file)

@app.route('/get_config', methods=['GET'])
@requires_auth
def get_config():
    config = retrieve_yaml_file()
    return jsonify(config)

@app.route('/update_config', methods=['POST'])
@requires_auth
def update_config():
    data = request.json
    config = retrieve_yaml_file()

    save_config(config)
    return jsonify({'message': 'Config updated'}), 200

@app.route('/get_trigger_status', methods=['GET'])
@requires_auth
def get_trigger_status():
    config = retrieve_yaml_file()
    return jsonify({
        'system': config.get('activity', {}).get('system', 0),
        'voltage': config.get('activity', {}).get('voltage', 0),
        'load': config.get('activity', {}).get('load', 0)
        })

# Change the color of the header based on this GET request
@app.route('/get_countdown_vars', methods=['GET'])
@requires_auth
def get_countdown_vars():
    countdown_dict = get_local_socket_info()

    return jsonify({
        'rpi_yea': countdown_dict.get("rpi_year", 0),
        'rpi_mon': countdown_dict.get("rpi_month", 0),
        'rpi_day': countdown_dict.get("rpi_day", 0),
        'rpi_h': countdown_dict.get("rpi_hour", 0),
        'rpi_m': countdown_dict.get("rpi_minute", 0),
        'rpi_s': countdown_dict.get("rpi_second", 0),

        'sys_activity': countdown_dict.get("sys_activity", 0),
        'sys_ch': countdown_dict.get("sys_countdown_hour", 0),
        'sys_cm': countdown_dict.get("sys_countdown_minute", 0),
        'sys_cs': countdown_dict.get("sys_countdown_second", 0),

        'volt_activity': countdown_dict.get("volt_activity", 0),
        'volt_ch': countdown_dict.get("volt_countdown_hour", 0),
        'volt_cm': countdown_dict.get("volt_countdown_minute", 0),
        'volt_cs': countdown_dict.get("volt_countdown_second", 0),

        'load_activity': countdown_dict.get("load_activity", 0),
        'load_ch': countdown_dict.get("load_countdown_hour", 0),
        'load_cm': countdown_dict.get("load_countdown_minute", 0),
        'load_cs': countdown_dict.get("load_countdown_second", 0)
    })

# Run the webserver
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)