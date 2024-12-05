from flask import Flask, render_template, request, redirect, jsonify, url_for, send_from_directory, send_file, after_this_request, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import socket
import math
import json
import paramiko
import random
import atexit
import platform
import os
from dotenv import load_dotenv
import time
import multiprocessing
import requests
import subprocess
import signal
import sys
from threading import Thread
import threading
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from networkscanner import NetworkScanner
from datetime import datetime, date, timedelta
from youtube_downloader import download_video, convert_to_ogg
from html_creator import create_html_file, create_room_folder
from functools import partial
import uuid
load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app)
#command = 'python relay_control.py'
if platform.system().lower() == "linux":
            # Use the following for Linux
    loadMqtt = True
else:
            # Use the following for non-Linux (assuming it's Windows in this case)
    loadMqtt = False
ssh = None
stdin = None
pi2 = None
pi3 = None
romy = True
room = None
last_keypad_code = None
aborted = False
language = {}
fade_duration = 3  # Fade-out duration in seconds
fade_interval = 0.1  # Interval between volume adjustments in seconds
fade_steps = int(fade_duration / fade_interval)  # Number of fade steps
sensor_1_triggered = False
sensor_2_triggered = False
ip_guard_room = '192.168.50.218'
ip_corridor = '192.168.50.197'
ip_cell = '192.168.50.242'
sequence = 0
sigil_count = 0
should_sound_play = True
should_balls_drop = True
code1 = False
code2 = False
code3 = False
code4 = False
code5 = False
kraken1 = False
kraken2 = False
kraken3 = False
kraken4 = False
codesCorrect = 0
bird_job = False
squeak_job = False
should_hint_shed_play = False
start_time = None
first_potion_solvable = False
second_potion_solvable = False
third_potion_solvable = False
fourth_potion_solvable = False
potion_count = 0
last_three_pulled = []  # List to keep track of the last three plants pulled
valid_combinations = {
    "green": ["ir-plant-5", "ir-plant-3", "ir-plant-8"],
    "orange": ["ir-plant-2", "ir-plant-9", "ir-plant-1"],
    "yellow": ["ir-plant-1", "ir-plant-6", "ir-plant-9"],
    "purple": ["ir-plant-3", "ir-plant-6", "ir-plant-7"]
}
CHECKLIST_FILE = 'checklist_data.json'
#logging.basicConfig(level=logging.DEBUG)  # Use appropriate log level
active_ssh_connections = {}
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
CORS(app)
scheduler = BackgroundScheduler()
scheduler.start()
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def turn_on_api():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip_guard_room, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
    ssh.exec_command('nohup sudo -E python status.py > /dev/null 2>&1 &')
    establish_ssh_connection()

def establish_ssh_connection():
    global ssh, stdin
    if ssh is None or not ssh.get_transport().is_active():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_guard_room, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
        ssh.exec_command('pkill -f mqtt.py')
    global pi2
    if pi2 is None or not pi2.get_transport().is_active():
        pi2 = paramiko.SSHClient()
        pi2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pi2.connect(ip_corridor, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
        pi2.exec_command('pkill -f mqtt.py')

    global pi3
    if pi3 is None or not pi3.get_transport().is_active():
        pi3 = paramiko.SSHClient()
        pi3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pi3.connect(ip_cell, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
        pi3.exec_command('pkill -f mqtt.py \n python status.py')

def is_online(ip):
    try:
        if platform.system().lower() == "linux":
            # Use the following for Linux
            response = subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL)
        else:
            # Use the following for non-Linux (assuming it's Windows in this case)
            response = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], stdout=subprocess.DEVNULL)

        return response.returncode == 0
    except Exception as e:
        print(f"Error pinging {ip}: {e}")
        return False

@app.route('/check_devices_status/<room>', methods=['GET'])
def check_devices_status(room):
    try:
        with open(f'json/{room}/raspberry_pis.json', 'r') as file:
            devices = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"error": "Failed to read Raspberry Pi data"}), 500

    for device in devices:
        device['online'] = is_online(device['ip_address'])

    return jsonify(devices)
@app.route('/list_raspberrypi')
def list_raspberrypi():
    scanner = NetworkScanner()
    pi_devices = scanner.scan_for_raspberrypi()
    return render_template('list_raspberrypi.html', devices=pi_devices)

def add_pi_to_json(ip_address, mac_address, hostname, file_path='json/raspberry_pis.json'):
    try:
        # Load existing data
        with open(file_path, 'r') as file:
            pis = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        pis = []

    # Check if the Raspberry Pi is already in the list
    for pi in pis:
        if pi['ip_address'] == ip_address:
            # Update existing entry
            pi['mac_address'] = mac_address
            pi['hostname'] = hostname
            break
    else:
        # Add new Raspberry Pi
        pis.append({"ip_address": ip_address, "mac_address": mac_address, "hostname": hostname})

    # Save the updated list
    with open(file_path, 'w') as file:
        json.dump(pis, file, indent=4)

@app.route('/connect_device', methods=['POST'])
def connect_device():
    ip_address = request.form['ip_address']
    new_hostname = request.form['new_hostname']
    scanner = NetworkScanner()

    # Connect to the Raspberry Pi and change its hostname
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
    ssh.exec_command(f'sudo hostnamectl set-hostname {new_hostname} \n sudo python /path/to/update_hosts.py')
    ssh.close()

    # Get the updated list of Raspberry Pis to fetch the MAC address
    pi_devices = scanner.scan_for_raspberrypi()
    mac_address = next((mac for host, mac, hostname in pi_devices if host == ip_address), None)

    # Update the JSON file with the Raspberry Pi's details
    if mac_address:
        add_pi_to_json(ip_address, mac_address, new_hostname)
    else:
        print("MAC address not found for the Raspberry Pi at", ip_address)

    return redirect(url_for('pow'))  # Redirect to a confirmation page or main page
#broker_ip = "192.168.18.66"
#broker_ip = "192.168.0.103"  # IP address of the broker Raspberry Pi
broker_ip = "100.100.182.106"
# Define the topic prefix to subscribe to (e.g., "sensor_state/")
prefix_to_subscribe = "state_data/"
sensor_states = {}
# Callback function to process incoming MQTT messages

pi_service_statuses = {}  # New dictionary to store service statuses for each Pi
twinkle_sequence = ["g", "g", "d", "d", "e", "e", "d"]
current_sequence = []

def load_rules(room):
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_sensor_data(room):
    try:
        with open(f"json/{room}/sensor_data.json", 'r') as json_file:
            return json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def reset_max_executions(room):
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            rules = json.load(file)
        for rule in rules:
            for constraint in rule['constraints']:
                if constraint['type'] == 'max-executions':
                    constraint['current_executions'] = 0
        with open(f'json/{room}/rules.json', 'w') as file:
            json.dump(rules, file, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def update_rule_executions(room, rule_id, constraint_type):
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            rules = json.load(file)
        for rule in rules:
            if rule['id'] == rule_id:
                for constraint in rule['constraints']:
                    if constraint['type'] == constraint_type and 'current_executions' in constraint:
                        constraint['current_executions'] += 1
        with open(f'json/{room}/rules.json', 'w') as file:
            json.dump(rules, file, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def evaluate_constraint(constraint, sensor_name, sensor_state, room, rule_id=None):
    sensor_data = get_sensor_data(room)
    if constraint['type'] == 'not':
        return not any(
            evaluate_constraint(nested_constraint, sensor_name, sensor_state, room, rule_id)
            for nested_constraint in constraint['nestedConstraints']
        )
    elif constraint['type'] == 'state-equals':
        for sensor in sensor_data:
            if sensor['name'].lower() == constraint.get('sensor').lower():
                return sensor['state'].lower() == constraint.get('state').lower()
        return False
    elif constraint['type'] == 'task-completed':
        task_state = check_task_state(constraint.get('task'), room)
        return task_state in [state.lower() for state in constraint.get('states', [])]
    elif constraint['type'] == 'max-executions':
        if 'current_executions' not in constraint:
            constraint['current_executions'] = 0
        if constraint['current_executions'] < int(constraint['max_executions']):
            if rule_id:
                update_rule_executions(room, rule_id, 'max-executions')
            return True
        return False
    return False

def handle_rules(sensor_name, sensor_state, room):
    if get_game_status(room) == {'status': 'playing'}:
        rules = load_rules(room)
        for rule in rules:
            constraints_met = all(
                evaluate_constraint(constraint, sensor_name, sensor_state, room, rule['id'])
                for constraint in rule['constraints']
            )
            if constraints_met:
                threading.Thread(target=execute_rule, args=(rule, room)).start()  # Run execute_rule in a separate thread

def update_sensor_state(room, sensor_name, increment_value):
    try:
        with open(f'json/{room}/sensor_data.json', 'r') as file:
            sensor_data = json.load(file)
        for sensor in sensor_data:
            if sensor['name'] == sensor_name:
                try:
                    current_state = sensor['state']
                    if current_state == "init":
                        current_state = 0
                    sensor['state'] = str(int(current_state) + increment_value)
                except ValueError:
                    print(f"Error: Sensor state for {sensor_name} is not an integer and cannot be incremented.")
                    return
        with open(f'json/{room}/sensor_data.json', 'w') as file:
            json.dump(sensor_data, file, indent=4)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error updating sensor state for {sensor_name}: {e}")

def execute_rule(rule, room):
    def execute_next_action(index):
        global language
        if index >= len(rule['actions']):
            return

        action = rule['actions'][index]
        if 'sensor' in action and 'state' in action:
            call_control_maglock_partial(room, action['sensor'], action['state'])
            execute_next_action(index + 1)
        elif 'task' in action and 'status' in action:
            solve_task(action['task'], room)
            execute_next_action(index + 1)
        elif 'delay' in action:
            time.sleep(int(action['delay']))
            execute_next_action(index + 1)
        elif 'play_sound' in action and 'volume' in action:
            for pi in action['pi']:
                current_game = get_game_data(room)[-1]  # Get the current game
                language = current_game.get("language", "nl")  # Default to Dutch if not found
                sound_prefix = "en/" if language == "eng" else ""
                publish.single(f"audio_control/{pi}/play", f"{action['volume']} {sound_prefix}{action['play_sound']}", hostname=broker_ip)
            execute_next_action(index + 1)
        elif 'increment' in action:
            update_sensor_state(room, action['sensor'], int(action['increment']))
            execute_next_action(index + 1)

    execute_next_action(0)

def plant_pulled(plant_name, room):
    global last_three_pulled

    # Check if the plant is in a "Not Triggered" state (pulled)
    if check_rule(plant_name, room):
        # Add the plant to the list of pulled plants
        last_three_pulled.append(plant_name)

        # Keep only the last three pulled plants
        if len(last_three_pulled) > 3:
            last_three_pulled.pop(0)
        TOPIC = f"led/control/mlv-herbalist/plants_pulled"
        pulled_plants_str = ",".join(last_three_pulled)
        publish.single(TOPIC, pulled_plants_str, hostname=broker_ip)
        # If exactly 3 plants are pulled, check if they match a valid combination
        if len(last_three_pulled) == 3:
            check_potion(room)

def check_potion(room):
    global last_three_pulled, first_potion_solvable, second_potion_solvable, third_potion_solvable, fourth_potion_solvable

    # Check if the last three pulled plants match any valid potion combination
    for color, combination in valid_combinations.items():
        if sorted(last_three_pulled) == sorted(combination):
            task_state = check_task_state(f"{color}-potion", room)
            if task_state == "pending":
                publish.single(f"led/control/mlv-herbalist", color, hostname=broker_ip)
                call_control_maglock_moonlight("humidifier", "unlocked")
                print(f"{color.capitalize()} potion is solvable!")

                # Set the correct solvable potion flag and reset others
                # reset_potion_flags()
                if color == "green":
                    first_potion_solvable = True
                elif color == "orange":
                    second_potion_solvable = True
                elif color == "purple":
                    third_potion_solvable = True
                elif color == "yellow":
                    fourth_potion_solvable = True
            return

    # If no match, reset the pulled plants list
    #last_three_pulled = []
    print("Wrong combination, try again.")

def reset_plants():
    global last_three_pulled
    last_three_pulled = []
    TOPIC = f"led/control/mlv-herbalist/plants_pulled"
    pulled_plants_str = ",".join(last_three_pulled)
    publish.single(TOPIC, pulled_plants_str, hostname=broker_ip)
    # Additional reset logic, if needed

def reset_potion_flags():
    global first_potion_solvable, second_potion_solvable, third_potion_solvable, fourth_potion_solvable
    first_potion_solvable = False
    second_potion_solvable = False
    third_potion_solvable = False
    fourth_potion_solvable = False
def on_message(client, userdata, message):
    global sensor_states, pi_service_statuses, code1, code2, code3, code4, code5, codesCorrect, sequence
    
    # Extract the topic and message payload
    topic = message.topic
    parts = topic.split("/")
    if len(parts) == 3 and parts[2] == "service_status":
        pi_name = parts[1]  # Extract the Pi name
        data = json.loads(message.payload.decode("utf-8"))
        
        # Check if the message is for service status
        if parts[2] == "service_status":
            # Update service status for the Pi
            pi_service_statuses[pi_name] = data
            print(f"Received service status from {pi_name}: {data}")
            
            # Now you can process the received service status data as needed
            # For example, check if all required services are active and take actions accordingly
            
            # Example: Check if all services are active for the Pi
            if all(status == "active" for status in data.values()):
                print(f"All services are active for {pi_name}")
            else:
                print(f"Not all services are active for {pi_name}")

        # For other types of messages (e.g., sensor states), you can handle them as before
    else:
        sensor_name = parts[-1]  # Extract the last part of the topic (sensor name)
        pi = parts[1]
        if "ret" in pi:
            room = "The Retriever"
        else:
            room = "Moonlight Village"
        sensor_state = message.payload.decode("utf-8")
        sensor_states[sensor_name] = sensor_state
        print(f"Received MQTT message - Sensor: {sensor_name}, State: {sensor_state}")

        if sensor_name in sensor_states:
            sensor_states[sensor_name] = sensor_state
            update_json_file(room)
            socketio.emit('sensor_update', room="all_clients")
            print("State changed. Updated JSON.")
        #print(sensor_states)
        threading.Thread(target=handle_rules, args=(sensor_name, sensor_state, room)).start()
                
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    join_room('all_clients')
    emit('join_room_ack', {'room': 'all_clients'})
@app.route('/lock', methods=['POST'])
def lock_route():
    try:
        task = request.json.get('task', '')
        is_checked = request.json.get('isChecked', False)
        roomName = request.json.get('roomName', '')
        # Determine the action based on the isChecked flag
        action = "unlocked" if is_checked else "locked"
        execute_lock_command(task, action)

        # Update the checklist status
        update_checklist(roomName, task, is_checked)
        socketio.emit('checklist_update', {'task': task, 'isChecked': is_checked}, room="all_clients")
        print(f"Locking action executed successfully for task: {task, is_checked}")
        return jsonify({'success': True, 'message': 'Locking action executed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def execute_lock_command(task, action):
    try:
        if task == "sluit het luik voor de ballen":
            call_control_maglock_retriever("ball-drop-lock", action)
        if task == "Doe het luik richting vakantie kamer dicht":
            call_control_maglock_retriever("lab-hatch-lock", action)
        if task == "Leg het laatste puzzelstuk in de schuur in de eerste kamer en doe de schuur dicht":
            call_control_maglock_retriever("shed-door-lock", action)
        if task == "Sta in de laatste kamer en sluit de schuifdeur.":
            call_control_maglock_retriever("sliding-door-lock", action)
        if task == "Sluit luik vanuit vakantiekamer naar de tuin, zorg ervoor dat deze goed vastzit!":
            call_control_maglock_retriever("doghouse-lock", action)
        if task == "(vanuit buiten de kamer) doe de entreedeur dicht":
            call_control_maglock_retriever("entrance-door-lock", action)
        if task == "Gang-leds aan":
            publish.single("led/control/mlv-corridors", action, hostname=broker_ip)
        
    except Exception as e:
        print(f"Error executing {action} command: {str(e)}")


def update_checklist(room, task, is_checked):
    try:
        checklist_file_path = get_checklist_file_path(room)
        # Read the current checklist data
        with open(checklist_file_path, 'r') as file:
            checklist_data = json.load(file)

        # Find the task in the checklist and update its completed status
        for item in checklist_data:
            if item['task'] == task:
                item['completed'] = is_checked

        # Write the updated data back to the file
        with open(checklist_file_path, 'w') as file:
            json.dump(checklist_data, file, indent=2)
    except Exception as e:
        print(f"Error updating checklist: {str(e)}")
def get_checklist_file_path(room_name):
    return os.path.join('json', room_name, 'checklist_data.json')

@app.route('/get-checklist/<room>', methods=['GET'])
def get_checklist_route(room):
    try:
        checklist_file_path = get_checklist_file_path(room)
        checklist = get_checklist(checklist_file_path)
        return jsonify({'success': True, 'checklist': checklist})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def get_checklist(checklist_file_path):
    try:
        # Read the current checklist data
        with open(checklist_file_path, 'r') as file:
            checklist_data = json.load(file)

        return checklist_data
    except Exception as e:
        print(f"Error getting checklist: {str(e)}")
        return []
def check_task_state(task_name, room):
    json_file_path = f'json/{room}/tasks.json'  # Set the path to your JSON file
    with open(json_file_path, 'r') as json_file:
        task_data = json.load(json_file)

    for task in task_data:
        if task["task"] == task_name:
            return task["state"]
    return "Task not found"
def update_json_file(room):
    try:
        # Read existing JSON data
        with open(f"json/{room}/sensor_data.json", 'r') as json_file:
            sensor_data = json.load(json_file)

        # Update sensor states in the JSON data
        for sensor in sensor_data:
            sensor_name = sensor["name"]
            if sensor_name in sensor_states:
                sensor["state"] = sensor_states[sensor_name]

        # Write the updated JSON data back to the file
        with open(f"json/{room}/sensor_data.json", 'w') as json_file:
            json.dump(sensor_data, json_file, indent=4)

    except Exception as e:
        print(f"Error updating JSON file: {e}")
@app.route('/get_sensor_data/<room>', methods=['GET'])
def read_sensor_data(room):
    file_path = os.path.join('json', room, 'sensor_data.json')
    with open(file_path, "r") as file:
        sensor_data = json.load(file)
    return jsonify(sensor_data)
def read_sensor_data2(room):
    with open(f"json/{room}/sensor_data.json", "r") as file:
        sensor_data = json.load(file)
    return sensor_data
def check_rule(item_name, room):
    try:
        # Read sensor data from the JSON file
        with open(f"json/{room}/sensor_data.json", 'r') as json_file:
            state_data = json.load(json_file)

        # Find the sensor with the specified name
        item = next((i for i in state_data if i["name"] == item_name), None)

        if item:
            item_type = item.get("type")  # Default to "sensor" if type is not specified
            item_name = item.get("name")
            # Special condition for IR sensors
            if room == "Moonlight Village":
                if item_type == "Sensor" and "ir" in item_name.lower():
                    if item["state"] == "Not Triggered":
                        return True
                    else:
                        return False
            # General conditions for other sensors and devices
            if item_type == "Sensor" and item["state"] == "Triggered":
                return True
            elif item_type == "light" and item["state"] == "On":
                return True
            elif item_type == "maglock" and item["state"] == "Locked":
                return True
            elif item_type == "button" and item["state"] == "Triggered":
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
client = mqtt.Client()

    # Set the callback function for incoming MQTT messages
client.on_message = on_message

    # Connect to the MQTT broker
client.connect(broker_ip, 1883)

    # Subscribe to all topics under the specified prefix
client.subscribe(prefix_to_subscribe + "#")  # Subscribe to all topics under the prefix
# Function to execute the delete-locks.py script
client.loop_start()

@app.route('/trigger', methods=['POST'])
def trigger():
    # Process the data and respond as needed
    return jsonify({'message': 'Data received successfully'})
@app.route('/retriever')
def pow():
    return render_template('rooms/pow.html')
def start_scripts():
    return "nothing"


def get_music_files():
    music_files = []
    music_folder = 'static/Music'  # Update this with your music folder path
    for file in os.listdir(music_folder):
        if file.endswith('.ogg'):
            music_files.append(file)
    return music_files
def synchronize_music_files(new_music_file):
    with open('json/Moonlight Village/raspberry_pis.json') as f:
        raspberry_pis = json.load(f)
    for pi in raspberry_pis:
        if 'services' in pi and 'sound' in pi['services']:
            ip_address = pi['ip_address']
            username = os.getenv("SSH_USERNAME")
            password = os.getenv("SSH_PASSWORD")
            
            # SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip_address, username=username, password=password)
            
            # SFTP transfer
            sftp = ssh.open_sftp()
            sftp.put('static/Music/' + new_music_file, '/home/pi/Music/' + new_music_file)
            sftp.close()
            ssh.close()
@app.route('/media_control')
def media_control():
    music_files = get_music_files()
    return render_template('media_control.html', music_files=music_files)

@app.route('/music/<path:filename>')
def download_file(filename):
    return send_from_directory('static/Music', filename)
@app.route('/add_music', methods=['POST'])
def add_music():
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            new_music_file = file.filename
            file.save(os.path.join('static/Music', new_music_file))
            time.sleep(1)
            synchronize_music_files(new_music_file)
    return redirect(url_for('media_control'))

@app.route('/remove_music/<filename>')
def remove_music(filename):
    os.remove(os.path.join('static/Music', filename))
    return redirect(url_for('media_control'))
@app.route('/delete_music', methods=['POST'])
def delete_music():
    file = request.form.get('file')
    if file:

        try:
            # Create an SFTP client to delete the selected file
            sftp = pi2.open_sftp()
            
            # Delete the selected file from the Music folder
            remote_path = '/home/pi/Music/' + file
            sftp.remove(remote_path)
            
            return redirect('/media_control')
        except IOError as e:
            return f'Error: {str(e)}'
        finally:
            # Close the SFTP client and SSH connection
            sftp.close()
    else:
        return 'No file selected.'
@app.route('/pin-info')
def pin_info():
    return render_template('pin_info.html')
# Global variable to keep track of the currently playing music file
current_file = None

@app.route('/get_played_music_status', methods=['GET'])
def get_played_music_status():
    global current_file

    if current_file:
        file_data = [{'filename': current_file, 'status': 'playing'}]
    else:
        file_data = []

    return jsonify(file_data)
def fade_music_out(file, room):
    global broker_ip
    print(file)
    if room == "The Retriever":
        if file == "Lounge":
            initial_volume = 70
            final_volume = 0
        else:
            initial_volume = 35
            final_volume = 10

        # Gradually increase the volume
        current_volume = initial_volume
        while current_volume > final_volume:
            current_volume -= 1  # Increase volume by 1 each second
            payload = f"{int(current_volume)} {file}.ogg"
            if file == "Lounge":
                publish.single("audio_control/ret-top/volume", payload, hostname=broker_ip)
            else:
                publish.single("audio_control/ret-top/volume", payload, hostname=broker_ip)
            print(current_volume)
            if file == "alarm":
                time.sleep(0.05)
            else:
                time.sleep(0.05)
        if file != "Lounge":
            publish.single("audio_control/all_retriever/play", "prehint.ogg", hostname=broker_ip)
    else:
        initial_volume = 70
        final_volume = 5
        current_volume = initial_volume
        while current_volume > final_volume:
            current_volume -= 1
            payload = f"{int(current_volume)} {file}.ogg"
            publish.single("audio_control/raspberrypi/volume", payload, hostname=broker_ip)
            time.sleep(0.05)
    return "Volume faded successfully"
@app.route('/fade_music_out/<room>', methods=['POST'])
def fade_music_out_hint(room):
        # Gradually reduce the volume from 80 to 40
    if room == "The Retriever":
        for volume in range(35, 10, -1):
            # Send the volume command to the Raspberry Pi
            
            if check_task_state("squeekuence", room) == "solved":
                publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
            else:
                publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
            
            # Wait for a short duration between volume changes
            time.sleep(0.05)  # Adjust the sleep duration as needed
        time.sleep(1)
    else:
        if check_task_state("sigil-all", room) == "solved":
            for volume in range(150, 10, -1):
                # Send the volume command to the Raspberry Pi
                publish.single("audio_control/mlv-central/volume", f"{volume} tense.ogg", hostname=broker_ip)
                # Wait for a short duration between volume changes
                time.sleep(0.05)
        else:
            for volume in range(70, 10, -1):
                # Send the volume command to the Raspberry Pi
                publish.single("audio_control/mlv-central/volume", f"{volume} bg_central.ogg", hostname=broker_ip)
                # Wait for a short duration between volume changes
                time.sleep(0.05)
        time.sleep(1)
    if room == "The Retriever":
        publish.single("audio_control/all_retriever/play", "prehint.ogg", hostname=broker_ip)
        if check_task_state("squeekuence", room) == "solved":
            publish.single("audio_control/all_retriever/volume", "30 prehint.ogg", hostname=broker_ip)
    else:
        publish.single("audio_control/mlv-central/play", "prehint.ogg", hostname=broker_ip)
    return "Volume faded successfully"
@app.route('/fade_music_in/<room>', methods=['POST'])
def fade_music_in(room):
        # Gradually reduce the volume from 80 to 40
    if room == "The Retriever":
        for volume in range(10, 35, 1):
            # Send the volume command to the Raspberry Pi
            if check_task_state("squeekuence", room) == "solved":
                publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
            else:
                publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
            # Wait for a short duration between volume changes
            time.sleep(0.05)  # Adjust the sleep duration as needed
    else:
        if check_task_state("sigil-all", room) == "solved":
            for volume in range(10, 150, 1):
                # Send the volume command to the Raspberry Pi
                publish.single("audio_control/mlv-central/volume", f"{volume} tense.ogg", hostname=broker_ip)
                # Wait for a short duration between volume changes
                time.sleep(0.05)
        else:
            for volume in range(10, 70, 1):
                # Send the volume command to the Raspberry Pi
                publish.single("audio_control/mlv-central/volume", f"{volume} bg_central.ogg", hostname=broker_ip)
                # Wait for a short duration between volume changes
                time.sleep(0.05)
    return "Volume faded successfully"

# Route to display the SD Renewal page
@app.route('/sd-renewal')
def sd_renewal():
    with open('json/raspberry_pis.json') as f:
        pi_data = json.load(f)
    return render_template('sd_renewal.html', pi_data=pi_data)

current_dir = os.path.abspath(os.path.dirname(__file__))


@app.route('/get_file_status', methods=['GET'])
def get_file_status():
    file_path = os.path.join(current_dir, 'json', 'file_status.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                file_data = json.load(file)
            return jsonify(file_data)
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify([])
    else:
        return jsonify([])
    
@app.route('/get_task_status/<room>', methods=['GET'])
def get_task_status(room):
    tasks_file_path = os.path.join('json', room, 'tasks.json')
    games_file_path = os.path.join('json', room, 'data.json')

    if os.path.exists(tasks_file_path) and os.path.exists(games_file_path):
        try:
            with open(tasks_file_path, 'r') as tasks_file:
                tasks = json.load(tasks_file)

            with open(games_file_path, 'r') as games_file:
                games = json.load(games_file)

            current_game = games[-1] if games else None

            if current_game is None:
                return jsonify(tasks)

            start_time = datetime.fromisoformat(current_game['start_time'])
            task_states = current_game['tasks']

            for task in tasks:
                task_name = task['task']
                task['duration'] = None  
                task['state'] = task.get('state', 'pending')

                # Set duration if the task was solved in the current game
                if task_name in task_states and task_states[task_name]['state'] == 'solved':
                    solved_time = datetime.fromisoformat(task_states[task_name]['timestamp'])
                    duration = solved_time - start_time
                    minutes, seconds = divmod(duration.total_seconds(), 60)
                    task['duration'] = f"{int(minutes)}:{int(seconds):02d}"

                # Determine if the task is blocked based on its dependencies in tasks.json
                if 'depends_on' in task:
                    dependencies = task['depends_on']
                    task['blocked'] = not all(
                        next((t['state'] for t in tasks if t['task'] == dep), 'pending') in ['solved', 'skipped']
                        for dep in dependencies
                    )
                else:
                    task['blocked'] = False

            return jsonify(tasks)

        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify([])

    else:
        return jsonify([])
    
@app.route('/solve_task/<task_name>/<room>', methods=['POST'])
def solve_task(task_name, room):
    global start_time, sequence, code1, code2, code3, code4, code5, codesCorrect, squeak_job, bird_job, should_hint_shed_play, sigil_count
    global first_potion_solvable, second_potion_solvable, third_potion_solvable, fourth_potion_solvable, potion_count
    global new_init_time, timer_values, new_init_time_retriever, new_init_time_moon, language
    file_path = os.path.join('json', room, 'tasks.json')
    data_file_path = os.path.join('json', room, 'data.json')
    rules_path = os.path.join('json', room, 'rules.json')
    game_status = get_game_status(room)
    game_data = get_game_data(room)

    # Retrieve the latest game entry
    if game_data:
        current_game = game_data[-1]  # Assuming the last game is the current one
        if "tasks" not in current_game:
            current_game["tasks"] = {}

        # Mark task as solved with a timestamp
        current_game["tasks"][task_name] = {
            "state": "solved",
            "timestamp": datetime.now().isoformat()
        }

        # Save the updated game data back to data.json
        save_game_data(room, game_data)
        language = current_game.get("language", "nl")  # Default to Dutch if not found
        sound_prefix = "en/" if language == "eng" else ""
    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)
        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'solved'
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)
        socketio.emit('task_update', room="all_clients")

        # Handle rules for the solved task
        handle_rules(task_name, "solved", room)
        with app.app_context():
            return jsonify({'message': 'Task updated successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error updating task'})
PRESETS_FILE = 'json/Moonlight Village/presets.json'
@app.route('/presets', methods=['GET'])
def get_presets():
    """Retrieve the list of available presets."""
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, 'r') as f:
            presets = json.load(f)
        return jsonify(presets)
    else:
        return jsonify({'status': 'error', 'message': 'Presets file not found.'})
@app.route('/apply_preset', methods=['POST'])
def apply_preset():
    """Apply a selected preset."""
    data = request.json
    preset_name = data.get('preset')
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, 'r') as f:
            presets = json.load(f)
        preset = presets.get(preset_name)
        if preset:
            send_dmx_command(preset['pan'], preset['tilt'], preset['colour'], preset['gobo'], preset['smoke'])
            return jsonify({'status': 'success', 'message': f'Applied preset: {preset_name}'})
        else:
            return jsonify({'status': 'error', 'message': 'Preset not found.'})
    else:
        return jsonify({'status': 'error', 'message': 'Presets file not found.'})
MQTT_TOPIC = 'actuator/control/dmx/mlv-central'
def send_dmx_command(pan, tilt, colour, gobo, smoke):
    """Send DMX command via MQTT."""
    payload = {
        'pan': pan,
        'tilt': tilt,
        'colour': colour,
        'gobo': gobo,
        'smoke': smoke
    }
    payload_str = json.dumps(payload)
    publish.single(MQTT_TOPIC, payload=payload_str, qos=0, hostname=broker_ip)
    #print(f"Published to {MQTT_TOPIC}: {payload_str}")
sequence_running = False
@app.route('/dmx_control', methods=['GET', 'POST'])
def dmx_control():
    print("DMX control")
    if request.method == 'POST':
        try:
            pan = int(request.form['pan'])
            tilt = int(request.form['tilt'])
            colour = int(request.form['colour'])
            gobo = int(request.form['gobo'])
            smoke = int(request.form['smoke'])
            print(f'Pan: {pan}, Tilt: {tilt}, Colour: {colour}, Gobo: {gobo}, Smoke: {smoke}')
            send_dmx_command(pan, tilt, colour, gobo, smoke)
            return jsonify({'status': 'success', 'message': 'DMX command sent successfully!'})
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid input. Please enter valid numbers.'})
    return render_template('dmx_control.html')
def send_mqtt_message(message):
    publish.single(MQTT_TOPIC, payload=json.dumps(message), qos=1, hostname=broker_ip)
stop_event = threading.Event()
def interpolate(start, end, steps):
    """Helper function to generate smooth transitions."""
    step_size = (end - start) / steps
    return [start + step_size * i for i in range(steps)]
TOPIC_TAVERN = "led/control/mlv-tavern"
TOPIC_HERBALIST = "led/control/mlv-herbalist"
TOPIC_ASTRONOMY = "led/control/mlv-astronomy"
TOPIC_PLANTS = "led/control/mlv-plants"
def sequence_thread():
    global sequence_running
    try:
        sequence_duration = 0.03  # seconds per step
        steps_between_points = 50  # Adjust this for smoother transitions
        publish.single(TOPIC_TAVERN, "blink_red_climb", hostname=broker_ip)
        publish.single(TOPIC_TAVERN, "blink_red_tavern", hostname=broker_ip)
        publish.single(TOPIC_HERBALIST, "blink_green", hostname=broker_ip)
        publish.single(TOPIC_ASTRONOMY, "blink_green", hostname=broker_ip)
        publish.single(TOPIC_PLANTS, "blink_red_plants", hostname=broker_ip)
        publish.single(TOPIC_PLANTS, "blink_red_corridor", hostname=broker_ip) 
        # Define patrol points
        points = [
            {'pan': 172, 'tilt': 10},  # Point A
            {'pan': 150, 'tilt': 25},  # Point B
            {'pan': 165, 'tilt': 40},
            {'pan': 165, 'tilt': 65},  # Point C
            {'pan': 182, 'tilt': 75},  # Point D
            {'pan': 178, 'tilt': 35}, 
            {'pan': 192, 'tilt': 20}   # Point E
        ]
        cycle_count = 0

        while not stop_event.is_set():
            
            # Go through patrol points and perform DMX movement
            for i in range(len(points)):
                # Determine the next point (loop around to the first point)
                next_point = points[(i + 1) % len(points)]

                # Interpolate pan and tilt between the current and next points
                pan_values = interpolate(points[i]['pan'], next_point['pan'], steps_between_points)
                tilt_values = interpolate(points[i]['tilt'], next_point['tilt'], steps_between_points)

                # Send DMX commands for each step
                for pan_value, tilt_value in zip(pan_values, tilt_values):
                    if stop_event.is_set():
                        break  # Exit if stop event is triggered

                    # Send DMX command (rounding values)
                    send_dmx_command(round(pan_value), round(tilt_value), colour=12, gobo=0, smoke=0)
                    time.sleep(sequence_duration)

            cycle_count += 1
            print('Patrol completed one cycle!')

            # Randomize points every 2 full cycles
            if cycle_count % 16 == 0:  # Every 16 cycles
                publish.single(TOPIC_TAVERN, "blink_green_tavern", hostname=broker_ip)
                publish.single(TOPIC_TAVERN, "blink_red_climb", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_plants", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_corridor", hostname=broker_ip)
                call_control_maglock_moonlight("tavern-door-lock", "unlocked")
                call_control_maglock_moonlight("herbalist-door-lock", "locked")
                call_control_maglock_moonlight("astronomy-door-lock", "unlocked")
                call_control_maglock_moonlight("secret-door-lock", "unlocked")
                call_control_maglock_moonlight("corridor-door-lock", "unlocked")
                points = [
                    {'pan': 172, 'tilt': 10},  # Point A
                    {'pan': 150, 'tilt': 25},  # Point B
                    {'pan': 165, 'tilt': 40},
                    {'pan': 165, 'tilt': 65},  # Point C
                    {'pan': 182, 'tilt': 75},  # Point D
                    {'pan': 178, 'tilt': 35}, 
                    {'pan': 192, 'tilt': 20}   # Point E
                ]

            elif cycle_count % 14 == 0:  # Every 14 cycles
                random.shuffle(points)
                print('Points randomized! New order:', points)

            elif cycle_count % 12 == 0:  # Every 12 cycles
                publish.single(TOPIC_TAVERN, "blink_red_tavern", hostname=broker_ip)
                publish.single(TOPIC_TAVERN, "blink_red_climb", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_green", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_plants", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_corridor", hostname=broker_ip)
                points = [
                    {'pan': 172, 'tilt': 10},  # Point A
                    {'pan': 150, 'tilt': 25},  # Point B
                    {'pan': 165, 'tilt': 40},
                    {'pan': 165, 'tilt': 65},  # Point C
                    {'pan': 182, 'tilt': 75},  # Point D
                    {'pan': 178, 'tilt': 35}, 
                    {'pan': 192, 'tilt': 20}   # Point E
                ]

            elif cycle_count % 10 == 0:  # Every 10 cycles
                random.shuffle(points)
                print('Points randomized! New order:', points)

            elif cycle_count % 8 == 0:  # Every 8 cycles
                publish.single(TOPIC_TAVERN, "blink_red_tavern", hostname=broker_ip)
                publish.single(TOPIC_TAVERN, "blink_red_climb", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_green", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_green_plants", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_corridor", hostname=broker_ip)
                points = [
                    {'pan': 172, 'tilt': 10},  # Point A
                    {'pan': 150, 'tilt': 25},  # Point B
                    {'pan': 165, 'tilt': 40},
                    {'pan': 165, 'tilt': 65},  # Point C
                    {'pan': 182, 'tilt': 75},  # Point D
                    {'pan': 178, 'tilt': 35}, 
                    {'pan': 192, 'tilt': 20}   # Point E
                ]

            elif cycle_count % 6 == 0:  # Every 6 cycles
                random.shuffle(points)
                print('Points randomized! New order:', points)

            elif cycle_count % 4 == 0:  # Every 4 cycles
                publish.single(TOPIC_TAVERN, "blink_green_climb", hostname=broker_ip)
                publish.single(TOPIC_TAVERN, "blink_red_tavern", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_red_plants", hostname=broker_ip)
                publish.single(TOPIC_PLANTS, "blink_green_corridor", hostname=broker_ip)
                points = [
                    {'pan': 172, 'tilt': 10},  # Point A
                    {'pan': 150, 'tilt': 25},  # Point B
                    {'pan': 165, 'tilt': 40},
                    {'pan': 165, 'tilt': 65},  # Point C
                    {'pan': 182, 'tilt': 75},  # Point D
                    {'pan': 178, 'tilt': 35}, 
                    {'pan': 192, 'tilt': 20}   # Point E
                ]

            elif cycle_count % 2 == 0:  # Every 2 cycles
                random.shuffle(points)
                print('Points randomized! New order:', points)
        print('Sequence stopped successfully!')

    except Exception as e:
        print(f'Error in sequence: {str(e)}')
@app.route('/start_sequence', methods=['POST'])
def start_sequence():
    global sequence_running, stop_event
    if sequence_running:
        return jsonify({'message': 'Sequence already running!', 'status': 'error'})

    try:
        # Reset stop_event in case it was set previously
        stop_event.clear()
        sequence_running = True
        # Start the sequence in a separate thread
        threading.Thread(target=sequence_thread).start()
        return jsonify({'message': 'Patrol sequence started successfully!', 'status': 'success'})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'})

@app.route('/stop_sequence', methods=['POST'])
def stop_sequence():
    global sequence_running, stop_event
    if not sequence_running:
        return jsonify({'message': 'No sequence running!', 'status': 'error'})

    sequence_running = False
    # Set the event to signal the thread to stop
    stop_event.set()
    # Reset DMX values to 0
    send_dmx_command(0, 0, 0, 0, 0)
    return jsonify({'message': 'Sequence stopped and DMX values reset to 0.', 'status': 'success'})
@app.route('/skip_task/<task_name>/<room>', methods=['POST'])
def skip_task(task_name, room):
    global bird_job, code1, code2, code3, code4, code5, sequence, codesCorrect
    file_path = os.path.join('json', room, 'tasks.json')

    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)

        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'skipped'
        if task_name == "tree-lights":
            code5 = True
            call_control_maglock_retriever("blue-led", "locked")
            call_control_maglock_retriever("green-led", "locked")
            call_control_maglock_retriever("red-led", "locked")
            if bird_job == True:
                scheduler.remove_job('birdjob')
                bird_job = False
        elif task_name == "flowers":
            code1 = True
            codesCorrect += 1
        elif task_name == "kite-count":
            code2 = True
            codesCorrect += 1
        elif task_name == "number-feel":
            code3 = True
            codesCorrect += 1
        elif task_name == "fence-decrypt":
            code4 = True
            codesCorrect += 1
        if code1 and code2 and code3 and code4 and code5:
            print("executed")
            publish.single("audio_control/ret-top/play", "schuur_open.ogg", hostname=broker_ip)
            call_control_maglock_retriever("shed-door-lock", "locked")
            code1 = False
            code2 = False
            code3 = False
            code4 = False
            code5 = False
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)
        socketio.emit('task_update', room="all_clients")
        # You can add any additional logic here for handling skipped tasks if needed.

        return jsonify({'message': 'Task skipped successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error skipping task'})
def cause_shortcircuit():
    return "shortcircuited"
@app.route('/pend_task/<task_name>/<room>', methods=['POST'])
def pend_task(task_name, room):
    file_path = os.path.join('json', room, 'tasks.json')

    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)

        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'pending'

        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)
        socketio.emit('task_update', room="all_clients")
        with app.app_context():
            return jsonify({'message': 'Task updated successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error updating task'})
@app.route('/reset_task_statuses/<room>', methods=['POST'])
def reset_task_statuses(room):
    global sequence, sigil_count, potion_count
    file_path = os.path.join('json', room, 'tasks.json')
    if room == "The Retriever":
        sequence = 0
    else:     
        sigil_count = 0
        potion_count = 0
        reset_plants()
        reset_potion_flags()
        publish.single("video_control/mlv-tavern/stop", "stop", hostname=broker_ip)
    update_game_status('awake', room)
    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)

        for task in tasks:
            task['state'] = 'pending'

        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)

        return jsonify({'message': 'Task statuses reset successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error resetting task statuses'})
def reset_prepare(room):
    file_path = os.path.join('json', room, 'tasks.json')
    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)

        for task in tasks:
            task['state'] = 'pending'

        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)

        return jsonify({'message': 'Task statuses reset successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error resetting task statuses'})

@app.route('/convert', methods=['POST'])
def convert():
    youtube_url = request.form['youtubeURL']
    # Remove any existing .ogg file before converting a new video
    remove_existing_ogg()
    video_file = download_video(youtube_url)
    ogg_file = convert_to_ogg(video_file)
    return send_file(ogg_file, as_attachment=True)

def remove_existing_ogg():
    # Remove any existing .ogg file
    for file in os.listdir("."):
        if file.endswith(".ogg"):
            os.remove(file)
@app.route('/reset_puzzles/<room>', methods=['POST'])
def reset_puzzles(room):
    global code1, code2, code3, code4, code5, sequence, codesCorrect, should_hint_shed_play
    update_game_status('awake', room)
    if room == "The Retriever":
        should_hint_shed_play = True
        codesCorrect = 0
        code1 = False
        code2 = False
        code3 = False
        code4 = False
        code5 = False
        publish.single("actuator/control/ret-laser", "0", hostname=broker_ip)
    return "puzzles reset"

# Function to read the retriever status from the JSON file
def read_game_status(room):
    with open(f'json/{room}/game_status.json', 'r') as file:
        data = json.load(file)
    return data.get('status', 'awake')  # Default status is 'awake'

# Function to update the retriever status in the JSON file
def update_game_status(status, room):
    data = {"status": status}
    with open(f'json/{room}/game_status.json', 'w') as file:
        json.dump(data, file)

@app.route('/get_game_status/<room>', methods=['GET'])
def get_game_status(room):
    game_status = read_game_status(room)
    return {"status": game_status}

@app.route('/wake_room/<room>', methods=['POST'])
def wake_room(room):
    # Update the retriever status to 'awake'
    try:
        with open(f'json/{room}/sensor_data.json', 'r') as file:
            devices = json.load(file)

        # Iterate over devices
        if room == "The Retriever":
            for device in devices:
                if device["type"] in ["light"] and device["name"] != "green-led" and device["name"] != "red-led" and device["name"] != "blue-led" and device["name"] != "red-led-keypad" and device["name"] != "green-led-keypad":
                    call_control_maglock_retriever(device["name"], "unlocked")
        else:
            publish.single("led/control/mlv-herbalist", "unlocked", hostname=broker_ip)
            publish.single("led/control/mlv-tavern", "unlocked", hostname=broker_ip)
            publish.single("led/control/mlv-astronomy", "unlocked", hostname=broker_ip)
            publish.single("led/control/mlv-corridors", "unlocked", hostname=broker_ip)
            publish.single("led/control/mlv-webcam", "unlocked", hostname=broker_ip)
            call_control_maglock_moonlight("lamp-post-1", "unlocked")
            call_control_maglock_moonlight("lamp-post-2", "unlocked")
        update_game_status('awake', room)
        return "room awakened"
    except Exception as e:
        update_game_status('awake', room)
        return jsonify({'success': False, 'error': str(e)})
@app.route('/control_light/<room>', methods=['POST'])
def control_light(room):
    light_name = request.json.get('light_name')
    if light_name == "Light-1" and check_rule("light-1-garden", room):
        call_control_maglock_retriever("light-1-garden", "locked")
    elif light_name == "Light-1":
        call_control_maglock_retriever("light-1-garden", "unlocked")
        print(light_name)
    elif light_name == "Light-2":
        call_control_maglock_retriever("light-2-garden", "locked" if check_rule("light-2-garden", room) else "unlocked")
    elif light_name == "Light-3":
        call_control_maglock_retriever("light-3-garden", "locked" if check_rule("light-3-garden", room) else "unlocked")
    elif light_name == "Light-4":
        call_control_maglock_retriever("light-4-garden", "locked" if check_rule("light-4-garden", room) else "unlocked")
    elif light_name == "Light-5":
        call_control_maglock_retriever("light-1-shed", "locked" if check_rule("light-1-shed", room) else "unlocked")
    elif light_name == "Light-6":
        call_control_maglock_retriever("light-1-alley", "locked" if check_rule("light-1-alley", room) else "unlocked")
    elif light_name == "Light-7":
        if check_rule("blacklight", room):
            call_control_maglock_retriever("blacklight", "locked")
            call_control_maglock_retriever("portal-light", "locked")
        else:
            call_control_maglock_retriever("blacklight", "unlocked")
            call_control_maglock_retriever("portal-light", "unlocked")
    return jsonify({'message': f'Light {light_name} control command executed successfully'})

@app.route('/snooze_game/<room>', methods=['POST'])
def snooze_game(room):
    try:
        update_game_status('snoozed', room)

        # Load device information from sensor_data.json
        with open(f'json/{room}/sensor_data.json', 'r') as file:
            devices = json.load(file)

        # Iterate over devices
        if room == "The Retriever":
            for device in devices:
                if device["type"] in ["maglock", "light"]:
                    call_control_maglock_retriever(device["name"], "locked")
                if device["name"] == "laser-1" or device["name"] == "laser-2" or device["name"] == "top_left_light" or device["name"] == "top_right_light" or device["name"] == "bottom_left_light" or device["name"] == "bottom_right_light":
                    call_control_maglock_retriever(device["name"], "unlocked")
        else:
            for device in devices:
                if device["type"] in ["maglock", "light"]:
                    call_control_maglock_moonlight(device["name"], "unlocked")
                if device["name"] == "rem-lamp":
                    call_control_maglock_moonlight(device["name"], "locked")
            publish.single("led/control/mlv-herbalist", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-tavern", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-astronomy", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-corridors", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-webcam", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-plants", "locked", hostname=broker_ip)
        return "Room snoozed"
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/data')
def data():
    return render_template('data_view.html')

@app.route('/data/<room>')
def get_data(room):
    try:
        with open(f'json/{room}/data.json', 'r') as file:
            data = json.load(file)
            print(data)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/add_task/<room>', methods=['POST'])
def add_task(room):
    file_path = os.path.join('json', room, 'tasks.json')
    task_data = request.get_json()

    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)
        
        tasks.append(task_data)

        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)

        return jsonify({'message': 'Task added successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error adding task'})
    
@app.route('/remove_task/<room>', methods=['POST'])
def remove_task(room):
    file_path = os.path.join('json', room, 'tasks.json')
    task_data = request.get_json()

    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)

        updated_tasks = [task for task in tasks if task['task'] != task_data['task']]

        with open(file_path, 'w') as file:
            json.dump(updated_tasks, file, indent=4)

        return jsonify({'message': f'Task "{task_data["task"]}" removed successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error removing task'})
@app.route('/edit_task', methods=['POST'])
def edit_task():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
    edit_data = request.get_json()

    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)

        # Find the task to edit by its name
        for task in tasks:
            if task['task'] == edit_data['task']:
                task['task'] = edit_data['editedTaskName']
                task['description'] = edit_data['editedTaskDescription']

        # Write the updated task list back to the JSON file
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)

        return jsonify({'message': 'Task updated successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error updating task'})

@app.route('/get_task_progress/<room>', methods=['GET'])
def get_task_progress(room):
    file_path = os.path.join('json', room, 'tasks.json')
    
    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)
        
        progress = {
            'tasks': tasks  # Send the full list of tasks with their states
        }
        return jsonify(progress)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'tasks': []})
def handle_preset(message_key):
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, 'r') as f:
            presets = json.load(f)
        preset = presets.get(message_key)
        if preset:
            call_control_maglock_moonlight("dmx-power", "unlocked")
            send_dmx_command(preset['pan'], preset['tilt'], preset['colour'], preset['gobo'], preset['smoke'])
@app.route('/play_music/<room>', methods=['POST'])
def play_music(room):
    data = request.json
    message = data.get('message')
    volume = data.get('volume', 50)
    selected_pis = data.get('selected_pis', [])
    for pi in selected_pis:
        publish.single(f"audio_control/{pi}/play", f"{volume} {message}", hostname=broker_ip)
    return jsonify({"status": "success"})
@app.route('/stop_music/<room>', methods=['POST'])
def stop_music(room):
    global squeak_job, bird_job
    if bird_job == True:
        scheduler.remove_job('birdjob')
        bird_job = False
    if squeak_job == True:
        scheduler.remove_job('squeakjob')
        squeak_job = False
    if room == "The Retriever":
        publish.single("audio_control/all_retriever/full_stop", "stop", hostname=broker_ip)
    else:
        publish.single("audio_control/all_moonlight/full_stop", "stop", hostname=broker_ip)
    # Wipe the entire JSON file by overwriting it with an empty list
    file_path = os.path.join(current_dir, 'json', 'file_status.json')
    with open(file_path, 'w') as file:
        json.dump([], file)
    return "Music stopped"

def control_maglock(room):
    global squeak_job, should_balls_drop, player_type
    maglock = request.form.get('maglock')
    action = request.form.get('action')
    #print(maglock)
    #print(action)
    sensor_data = read_sensor_data2(room)
    for sensor in sensor_data:
        if sensor['name'] == maglock and (sensor['type'] == 'maglock' or sensor['type'] == 'light'):
            pi_name = sensor['pi']
            connection_type = sensor.get('connection_type', 'NO')  # Default to NO if not specified
            if connection_type == 'NO':
                # Reverse the action for NC connection type
                action = 'locked' if action == 'unlocked' else 'unlocked'
            # Publish the MQTT message with the appropriate Pi's name
            mqtt_message = f"{sensor['pin']} {action}"
            publish.single(f"actuator/control/{pi_name}", mqtt_message, hostname=broker_ip)
            return "done"
        elif sensor['name'] == maglock and sensor['type'] == 'led':
            pi_name = sensor['pi']
            if action == 'unlocked':
                publish.single(f"led/control/{pi_name}", "unlocked", hostname=broker_ip)
            else:
                publish.single(f"led/control/{pi_name}", "locked", hostname=broker_ip)
            return "done"
@app.route('/control_maglock/<room>', methods=['POST'])
def control_maglock_route(room):
    return control_maglock(room)


def call_control_maglock_partial(room, maglock, action):
    global squeak_job, should_balls_drop, player_type
    sensor_data = read_sensor_data2(room)
    for sensor in sensor_data:
        if sensor['name'] == maglock and (sensor['type'] == 'maglock' or sensor['type'] == 'light'):
            pi_name = sensor['pi']
            connection_type = sensor.get('connection_type', 'NO')  # Default to NO if not specified
            if connection_type == 'NO':
                # Reverse the action for NC connection type
                action = 'locked' if action == 'unlocked' else 'unlocked'
            mqtt_message = f"{sensor['pin']} {action}"
            publish.single(f"actuator/control/{pi_name}", mqtt_message, hostname=broker_ip)
            return "done"

# Create a partial function with room argument already applied
call_control_maglock_retriever = partial(call_control_maglock_partial, "The Retriever")
call_control_maglock_moonlight = partial(call_control_maglock_partial, "Moonlight Village")

@app.route('/reset-checklist/<room>', methods=['POST'])
def reset_checklist(room):
    try:
        # Read the current checklist data
        with open(f'json/{room}/{CHECKLIST_FILE}', 'r') as file:
            checklist_data = json.load(file)

        # Reset the completed status of all tasks
        for item in checklist_data:
            item['completed'] = False

        # Write the updated data back to the file
        with open(f'json/{room}/{CHECKLIST_FILE}', 'w') as file:
            json.dump(checklist_data, file, indent=2)

        # Unlock all tasks
        if room == "The Retriever":
            call_control_maglock_retriever("ball-drop-lock", "locked")
            call_control_maglock_retriever("lab-hatch-lock", "locked")
            call_control_maglock_retriever("shed-door-lock", "locked")
            call_control_maglock_retriever("sliding-door-lock", "locked")
            call_control_maglock_retriever("doghouse-lock", "locked")
            call_control_maglock_retriever("entrance-door-lock", "locked")
        else:
            publish.single("webcam_control/mlv-webcam", "unsolved", hostname=broker_ip)
        # Emit checklist update event
        socketio.emit('checklist_update', "message", room="all_clients")

    except Exception as e:
        print(f"Error resetting checklist: {str(e)}")
    return jsonify({'success': True, 'message': 'Checklist reset successfully'})
@app.route('/add_sensor/<room>', methods=['GET', 'POST'])
def add_sensor(room):
    global sensors
    if request.method == 'POST':
        # Retrieve form data including the new 'connection_type' field
        name = request.form['name']
        item_type = request.form['type']
        pin = int(request.form['pin'])
        pi = request.form['pi']
        connection_type = request.form['connection_type']

        # Create a new sensor dictionary with the additional field
        new_sensor = {
            "name": name,
            "type": item_type,
            "pin": pin,
            "pi": pi,
            "state": "initial",
            "connection_type": connection_type
        }
        with open(f'json/{room}/sensor_data.json', 'r') as json_file:
            sensors = json.load(json_file)
        # Add the new sensor to the list
        sensors.append(new_sensor)

        # Save the updated sensor data to the JSON file
        with open(f'json/{room}/sensor_data.json', 'w') as json_file:
            json.dump(sensors, json_file, indent=4)
        update_sensor_data_on_pis(room)

        return redirect(url_for('list_sensors', room=room))

    return render_template('add_sensor.html')

def update_sensor_data_on_pis(room):
    success_message = "Sensor data updated successfully. Updated script sent to the following IP addresses:<br>"

    # Read Raspberry Pi data from JSON file
    with open(f'json/{room}/raspberry_pis.json') as json_file:
        raspberry_pis = json.load(json_file)

    for raspberry_pi in raspberry_pis:
        ip = raspberry_pi["ip_address"]
        try:
            # Create an SSH session for the Raspberry Pi
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))

            # Create an SFTP session over the existing SSH connection
            sftp = ssh.open_sftp()

            # Transfer the updated file to the Raspberry Pi
            sftp.put(f'json/{room}/sensor_data.json', '/home/pi/sensor_data.json')

            success_message += f"- {ip}<br>"

            # Close the SFTP session and SSH connection
            sftp.close()
            ssh.close()
        except Exception as e:
            return f'Error occurred while sending updated script to {ip}: {e}'

    return success_message


@app.route('/remove_sensor/<room>', methods=['GET', 'POST'])
def remove_sensor(room):
    # Access the global sensors variable
    global sensors

    # Read the existing sensor data from the JSON file for both GET and POST methods
    with open(f'json/{room}/sensor_data.json', 'r') as json_file:
        sensors = json.load(json_file)

    if request.method == 'POST':
        # Retrieve the selected sensor name to remove
        sensor_name_to_remove = request.form['sensor_name']

        # Remove the sensor from the list
        updated_sensors = [sensor for sensor in sensors if sensor['name'] != sensor_name_to_remove]

        # Save the updated sensor data back to the JSON file
        with open(f'json/{room}/sensor_data.json', 'w') as json_file:
            json.dump(updated_sensors, json_file, indent=4)

        # Update sensor data on the Raspberry Pi devices
        update_sensor_data_on_pis(room)

        # Redirect to the list_sensors view for the specific room
        return redirect(url_for('list_sensors', room=room))

    # Render the remove sensor page for GET requests
    return render_template('remove_sensor.html', sensors=sensors)
@app.route('/list_sensors/<room>')
def list_sensors(room):
    # Read the sensor data from the JSON file
    with open(f'json/{room}/sensor_data.json', 'r') as json_file:
        sensors = json.load(json_file)

    # Render the template with the updated sensor data
    return render_template('list_sensors.html', sensors=sensors)
def start_bird_sounds():
    publish.single("audio_control/ret-top/play", "Gull.ogg", hostname=broker_ip)
    publish.single("audio_control/ret-top/volume", "100 Gull.ogg", hostname=broker_ip)
    time.sleep(8)
    publish.single("audio_control/ret-top/play", "Duck.ogg", hostname=broker_ip)
    publish.single("audio_control/ret-top/volume", "50 Duck.ogg", hostname=broker_ip)
    time.sleep(8)
    publish.single("audio_control/ret-top/play", "Eagle.ogg", hostname=broker_ip)
    publish.single("audio_control/ret-top/volume", "50 Eagle.ogg", hostname=broker_ip)
def start_squeak():
    publish.single("audio_control/ret-top/play", "squeek.ogg", hostname=broker_ip)


@app.route('/send_script')
def send_script():
    script_path = 'test.py'
    target_ip = '192.168.1.28'
    target_username = 'pi'
    target_directory = '~/'

    # Construct the scp command
    scp_command = f'scp {script_path} {target_username}@{target_ip}:{target_directory}'

    try:
        # Execute the scp command
        subprocess.run(scp_command, shell=True, check=True)
        return 'Script sent successfully!'
    except subprocess.CalledProcessError as e:
        return f'Error occurred while sending script: {e}'
def synchronize_music_to_pi(pi_info, music_files):
    if 'services' in pi_info and 'sound' in pi_info['services']:
        ip_address = pi_info['ip_address']
        username = os.getenv("SSH_USERNAME")
        password = os.getenv("SSH_PASSWORD")

        # SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=username, password=password)

        try:
            # SFTP transfer for each music file
            sftp = ssh.open_sftp()
            for music_file in music_files:
                local_path = os.path.join('static/Music/', music_file)
                remote_path = os.path.join('/home/pi/Music/', music_file)
                sftp.put(local_path, remote_path)
            local_path = os.path.join('json/', 'sensor_data.json')
            remote_path = os.path.join('/home/pi/', 'sensor_data.json')
            sftp.put(local_path, remote_path)
            sftp.close()
        finally:
            # Close SSH connection
            ssh.close()
@app.route('/renew-sd', methods=['POST'])
def handle_renew_sd():
    selected_pi = request.form.get('pi')
    result = renew_sd(selected_pi)
    return result
def renew_sd(selected_pi):
    # Find the selected Pi's data
    with open('json/raspberry_pis.json') as f:
        pi_data = json.load(f)
    pi_info = next((pi for pi in pi_data if pi['hostname'] == selected_pi), None)
    
    if pi_info:
        # SSH into the Pi
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(pi_info['ip_address'], username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))

        try:
            # Change hostname
            stdin, stdout, stderr = ssh.exec_command(f'sudo hostnamectl set-hostname {pi_info["hostname"]}')
            print(stdout.read().decode('utf-8'))

            # Update /etc/hosts
            stdin, stdout, stderr = ssh.exec_command(f'sudo sed -i "s/.*raspberrypi/{pi_info["ip_address"]} {pi_info["hostname"]}/" /etc/hosts')
            print(stdout.read().decode('utf-8'))

            # Enable services if any are specified
            if 'services' in pi_info:
                for service in pi_info['services']:
                    stdin, stdout, stderr = ssh.exec_command(f'sudo systemctl enable {service}.service')
                    print(stdout.read().decode('utf-8'))
            music_files = os.listdir('static/Music')
            synchronize_music_to_pi(pi_info, music_files)
            # Reboot the Pi for changes to take effect
            ssh.exec_command('sudo reboot')

            return "SD Renewal Successful"
        finally:
            # Close SSH connection
            ssh.close()
    else:
        return "Pi Not Found"
def reset_sensors():
    global sensor_1_triggered, sensor_2_triggered
    if sensor_2_triggered or sensor_1_triggered:
        time.sleep(1)
        sensor_1_triggered = False
        sensor_2_triggered = False
        print("Trigger flags reset.")

def continuous_reset_sensors():
    while True:
        reset_sensors()
def execute_code():
    stdin.write('0\n')
    stdin.flush()
    print("Code executed on the server Pi.")

@app.route('/reboot_pi', methods=['POST'])
def reboot_pi():
    ip_address = request.form.get('ip_address')

    # Ensure IP address is provided
    if not ip_address:
        return jsonify({"error": "IP address is required"}), 400

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))

        # Sending the reboot command
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo reboot')

        # Optional: Wait for the command to complete and fetch the output
        # output = ssh_stdout.read().decode()

        ssh.close()
        return jsonify({"message": f"Reboot command sent to {ip_address}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/trigger', methods=['POST'])
def handle_trigger():
    global sensor_1_triggered, sensor_2_triggered

    sensor_data = request.get_json()
    # print("Sensor triggered:", sensor_data["sensor"])

    if sensor_data["sensor"] == "Sensor 1":
        sensor_1_triggered = True
    elif sensor_data["sensor"] == "Sensor 2":
        sensor_2_triggered = True
    elif sensor_data["sensor"] == "turn off":
        sensor_1_triggered = False
        sensor_2_triggered = False
    if sensor_1_triggered and sensor_2_triggered:
        execute_code()
    return "Trigger handled."
def handle_interrupt(signal, frame):
    client.loop_stop()
    print("Interrupt received. Shutting down...")
    # Add any additional cleanup or termination logic here
    sys.exit()
TIMER_FILE = 'timer_value.txt'  # File to store the timer value
timer_values = {}
timer_thread = None  # Reference to the timer thread
speed = {}
speed["The Retriever"] = 1
speed["Moonlight Village"] = 1
timer_running = {}
timer_threads = {}
def read_timer_value(room):
    try:
        with open(f'json/{room}/{TIMER_FILE}', 'r') as file:
            return float(file.read().strip())
    except FileNotFoundError:
        return timer_value  # Default timer value if the file doesn't exist

def write_timer_value(value, room):
    with open(f'json/{room}/{TIMER_FILE}', 'w') as file:
        file.write(str(value))

def update_timer(room):
    global timer_values, timer_running, speed
    timer_value = timer_values[room]
    while timer_values[room] > 0 and timer_running[room]:
        timer_values[room] = max(timer_values[room] - speed[room], 0)
        #timer_values[room] = timer_value
        write_timer_value(timer_values[room], room)
        socketio.emit('timer_update', room="all_clients")
        time.sleep(1)
new_init_time_retriever = 3600
new_init_time_moon = 3600
@app.route('/add_minute/<room>', methods=['POST'])
def add_minute(room):
    global new_init_time, timer_values, new_init_time_retriever, new_init_time_moon
    timer_values[room] += 60
    if room == "The Retriever":
        new_init_time_retriever += 60
    else:
        new_init_time_moon += 60
    current_time = read_timer_value(room)
    new_time = current_time + 60
    write_timer_value(new_time, room)
    return "added"
@app.route('/remove_minute/<room>', methods=['POST'])
def remove_minute(room):
    global new_init_time, timer_values, new_init_time_retriever, new_init_time_moon
    timer_values[room] -= 60
    if room == "The Retriever":
        new_init_time_retriever -= 60
    else:
        new_init_time_moon -= 60
    current_time = read_timer_value(room)
    new_time = current_time - 60
    write_timer_value(new_time, room)
    return "removed"
@app.route('/initial_time/<room>', methods=['GET'])
def get_initial_time(room):
    global new_init_time_retriever, new_init_time_moon
    if room == "The Retriever":
        return str(new_init_time_retriever)
    elif room == "Moonlight Village":
        return str(new_init_time_moon)
@app.route('/game_data', methods=['GET'])
def get_game_data():
    file_path = 'json/game_data.json'
    game_data = []

    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            game_data = json.load(json_file)

    return jsonify(game_data)
@app.route('/game_data.html')
def game_data():
    return render_template('game_data.html')
def write_game_data(start_time, end_time):
    data = {
        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S')
    }
    file_path = 'json/game_data.json'

    # Check if the directory exists, create if not
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Load existing data if the file exists
    existing_data = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            existing_data = json.load(json_file)

    # Append new data to the list
    existing_data.append(data)

    # Write the updated list back to the file
    with open(file_path, 'w') as json_file:
        json.dump(existing_data, json_file, indent=2)
def get_game_data(room):
    # Path to the data.json file
    data_file_path = os.path.join('json', room, 'data.json')
    # Ensure data.json exists with an empty array if it doesn't
    if not os.path.exists(data_file_path):
        with open(data_file_path, 'w') as file:
            json.dump([], file)  # Initialize with an empty list
    # Load existing game data
    with open(data_file_path, 'r') as file:
        game_data = json.load(file)
    # Ensure the file content is a list
    if not isinstance(game_data, list):
        game_data = []
    return game_data

def save_game_data(room, game_data):
    data_file_path = os.path.join('json', room, 'data.json')
    with open(data_file_path, 'w') as file:
        json.dump(game_data, file, indent=4)
@app.route('/timer/start/<room>', methods=['POST'])
def start_timer(room):
    global timer_value, speed, timer_running, timer_thread, start_time, bird_job, language
    game_id = str(uuid.uuid4())
    # Create new game entry
    new_game = {
        "id": game_id,
        "room": room,
        "start_time": datetime.now().isoformat(),
        "tasks": {},
        "language": language.get(room, 'nl')
    }
    # Load existing game data and append the new game
    game_data = get_game_data(room)
    game_data.append(new_game)  # Append new game to list
    save_game_data(room, game_data)
    socketio.emit('reset_task_durations', room="all_clients")
    # Start a new timer thread for the room if not already running
    if room not in timer_threads or not timer_threads[room].is_alive():
        speed[room] = 1  # Reset timer speed to 1
        timer_values[room] = 3600  # Reset timer value to 60 minutes
        write_timer_value(timer_values[room], room)
        timer_running[room] = True
        timer_threads[room] = Thread(target=update_timer, args=(room,))
        timer_threads[room].daemon = True
        timer_threads[room].start()
        socketio.emit('sensor_update', room="all_clients")
        # Your existing code to start the timer
        update_game_status('playing', room)
        if bird_job == False and room == "The Retriever":
            scheduler.add_job(start_bird_sounds, 'interval', minutes=1, id='birdjob')
            bird_job = True
        start_time = datetime.now()
        if room == "The Retriever":
            fade_music_out("Lounge", room)
            time.sleep(1)
            publish.single("audio_control/ret-top/play", "Ambience.ogg", hostname=broker_ip)
            fade_music_in(room)
        else:
            publish.single("video_control/mlv-tavern/play", "fireplace.mp4", hostname=broker_ip)
            call_control_maglock_moonlight("entrance-door-lock", "locked")
            send_dmx_command(0, 0, 0, 0, 255)
            time.sleep(9)
            send_dmx_command(0, 0, 0, 0, 0)
        return 'Timer started'
@app.route('/timer/stop/<room>', methods=['POST'])
def stop_timer(room):
    global timer_thread, timer_running, kraken1, kraken2, kraken3, kraken4, bird_job, start_time, sigil_count
    if room in timer_threads and timer_threads[room].is_alive():
        timer_running[room] = False
        print("Stopping timer thread")
        timer_threads[room].join()
        update_game_status('awake', room)
        stop_sequence()
        del timer_threads[room]
        reset_task_statuses(room)
        reset_checklist(room)
        reset_timer_speed(room)
        end_time = datetime.now()
        socketio.emit('sensor_update', room="all_clients")
    stop_music(room)
    if start_time is not None:
        write_game_data(start_time, end_time)
    start_time = None

    return 'Timer stopped'

@app.route('/timer/speed/<room>', methods=['POST'])
def update_timer_speed(room):
    global speed
    change = float(request.form['change'])  # Get the change in timer speed from the request
    speed[room] += change
    return 'Timer speed updated'

@app.route('/timer/reset-speed/<room>', methods=['POST'])
def reset_timer_speed(room):
    global speed
    speed[room] = 1
    return 'Timer speed reset'

@app.route('/timer/value/<room>', methods=['GET'])
def get_timer_value(room):
    return str(read_timer_value(room))

@app.route('/timer/get-speed/<room>', methods=['GET'])
def get_timer_speed(room):
    global speed
    return str(speed[room])

@app.route('/timer/pause/<room>', methods=['POST'])
def pause_timer(room):
    global timer_thread, timer_running

    if timer_thread is not None and timer_thread.is_alive() and timer_running:
        timer_running = False
        return 'Timer paused'
    else:
        return 'Timer is not running or already paused'

@app.route('/timer/continue/<room>', methods=['POST'])
def continue_timer(room):
    global timer_thread, timer_running
    current_game_state = get_game_status()
    if current_game_state == {'status': 'prepared'}:
        update_game_status('playing', room)
    if timer_thread is not None and not timer_thread.is_alive() and not timer_running:
        timer_running = True
        timer_thread = threading.Thread(target=update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        return 'Timer continued'
    else:
        return 'Timer is already running or not paused'
@app.route('/timer/pause-state/<room>', methods=['GET'])
def get_pause_state(room):
    global timer_running
    return jsonify(timer_running)
@app.route('/get-pi-status', methods=['GET'])
def get_pi_status():
    global ssh, pi2, pi3
    # Define the names and IP addresses of the Pis
    pi_names = {
        "top-pi": "192.168.0.104",
        "middle-pi": "192.168.0.105",
        "tree-pi": "192.168.0.114"
    }

    # Prepare a list of dictionaries containing Pi status data
    pi_statuses = []

    if ssh:
        pi1_status = {"name": "top-pi", "ip_address": pi_names["top-pi"]}
        try:
            if ssh.get_transport().is_active():
                pi1_status["ssh_active"] = "Online"
            else:
                pi1_status["ssh_active"] = "Offline"
        except AttributeError:
            pi1_status["ssh_active"] = "Offline"
        pi_statuses.append(pi1_status)

    if pi2:
        pi2_status = {"name": "middle-pi", "ip_address": pi_names["middle-pi"]}
        try:
            if pi2.get_transport().is_active():
                pi2_status["ssh_active"] = "Online"
            else:
                pi2_status["ssh_active"] = "Offline"
        except AttributeError:
            pi2_status["ssh_active"] = "Offline"
        pi_statuses.append(pi2_status)

    if pi3:
        pi3_status = {"name": "tree-pi", "ip_address": pi_names["tree-pi"]}
        try:
            if pi3.get_transport().is_active():
                pi3_status["ssh_active"] = "Online"
            else:
                pi3_status["ssh_active"] = "Offline"
        except AttributeError:
            pi3_status["ssh_active"] = "Offline"
        pi_statuses.append(pi3_status)

    # Render the template fragment and return as JSON
    return jsonify(render_template('status_table_fragment.html', pi_statuses=pi_statuses))
# def check_service_status(ip_address, service_name):
#     ssh = paramiko.SSHClient()
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
#     stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service_name}')
#     status = stdout.read().decode().strip() == 'active'
#     ssh.close()
#     return status

# def restart_service(ip_address, service_name):
#     ssh = paramiko.SSHClient()
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
#     ssh.exec_command(f'sudo systemctl restart {service_name}')
#     ssh.close()

def get_raspberry_pis_with_prefix(prefix, scanner):
    pi_devices = scanner.scan_for_raspberrypi()
    pi_info = {hostname: {"ip_address": ip, "services": []} for ip, _, hostname in pi_devices if hostname and hostname.startswith(prefix)}
    return pi_info

def get_required_services():
    with open('json/raspberry_pis.json', 'r') as file:
        data = json.load(file)
    return {entry["hostname"]: entry.get("services", []) for entry in data}
def wait_for_statuses(pi_config, timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if all(pi['hostname'] in pi_service_statuses for pi in pi_config):
            break
        time.sleep(0.5)
    else:
        print("Timeout waiting for service statuses.")
pi_service_statuses = {}
preparedValue = {}
timeout_duration = 3
@app.route('/prepare/<room>', methods=['POST'])
def prepare_game(room):
    global client, pi_service_statuses, language, preparedValue, should_hint_shed_play, new_init_time

    # Set initial preparation time
    new_init_time = 3600

    # Define prefix based on room
    if room == "The Retriever":
        should_hint_shed_play = True
        prefix = "ret"
    else:
        prefix = "mlv"

    print(f"Preparing {room} with prefix {prefix}")

    # Check if the room is already prepared
    if get_game_status(room) == {'status': 'prepared'}:
        return jsonify({"message": preparedValue}), 200

    reset_prepare(room)
    reset_max_executions(room)  # Reset max-executions count

    # Load Raspberry Pi configuration from JSON file
    with open(f'json/{room}/raspberry_pis.json', 'r') as file:
        pi_config = json.load(file)

    # Create a list to hold threads for parallel execution
    threads = []
    
    # Loop over each Raspberry Pi and request service statuses asynchronously
    for pi in pi_config:
        if "services" in pi and pi["hostname"].startswith(prefix):
            hostname = pi["hostname"]
            services = pi["services"]
            ip_address = pi["ip_address"]
            print(f"Requesting service statuses for {hostname} ({services})")

            # Health check before requesting statuses
            if not check_service_status(ip_address):
                print(f"Service on {hostname} is not responding. Restarting service.")
                restart_service(ip_address)
                if not check_service_status(ip_address):
                    print(f"Service on {hostname} failed to restart. Marking all services as inactive.")
                    pi_service_statuses[hostname] = {service: "inactive" for service in pi["services"]}
                    continue  # Skip further processing for this Pi
            
            # Start a new thread to request service statuses for each Raspberry Pi
            thread = threading.Thread(target=request_service_status, args=(hostname, services, ip_address))
            threads.append(thread)
            thread.start()

    # Wait for all threads to complete, handle timeouts
    for thread in threads:
        thread.join(timeout=timeout_duration)

    # Check if any Raspberry Pi did not return within the timeout period
    for pi in pi_config:
        if pi["hostname"] not in pi_service_statuses:
            print(f"Timeout: No response from {pi['hostname']}. Marking all services as inactive.")
            pi_service_statuses[pi["hostname"]] = {service: "inactive" for service in pi["services"]}

    # Convert service statuses to True/False based on "active"/"inactive"
    converted_statuses = {}
    for pi, status_dict in pi_service_statuses.items():
        converted_statuses[pi] = {service: status == "active" for service, status in status_dict.items()}

    # Store the prepared status
    preparedValue = converted_statuses

    # Set language preferences
    if not isinstance(language, dict):
        language = {}
    language[room] = request.form.get('language')

    # Update game status to "prepared"
    update_game_status("prepared", room)
    time.sleep(0.1)

    # Perform actions based on the room type
    if room == "The Retriever":
        publish.single("audio_control/ret-top/play", "Lounge.ogg", hostname=broker_ip)
        if language[room] == "eng":
            publish.single("actuator/control/ret-laser", "en", hostname=broker_ip)
        elif language[room] == "nl":
            publish.single("actuator/control/ret-laser", "nl", hostname=broker_ip)
    else:
        publish.single("audio_control/raspberrypi/play", "bg_corridor.ogg", hostname=broker_ip)
        publish.single("led/control/mlv-corridors", "unlocked", hostname=broker_ip)
        call_control_maglock_moonlight("smoke-power", "unlocked")

    return jsonify({"message": converted_statuses}), 200

def check_service_status(ip_address):
    """ Function to check if the service_status service is active on the Raspberry Pi """
    try:
        result = subprocess.run(
            ['sshpass', '-p', SSH_PASSWORD, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{SSH_USERNAME}@{ip_address}', 
             'systemctl', 'is-active', '--quiet', 'service_status.service'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # If the service is active, it will return 0
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking service status for {ip_address}: {e}")
        return False

def restart_service(ip_address):
    """ Function to restart the service_status service on the Raspberry Pi """
    try:
        subprocess.run(
            ['sshpass', '-p', SSH_PASSWORD, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{SSH_USERNAME}@{ip_address}', 
             'sudo', 'systemctl', 'restart', 'service_status.service'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"Service on {ip_address} has been restarted.")
    except Exception as e:
        print(f"Error restarting service for {ip_address}: {e}")

def request_service_status(hostname, services, ip_address):
    """ Function to request the status of services from the Raspberry Pi """
    try:
        # Query service statuses via SSH and update pi_service_statuses
        service_status = {}
        for service in services:
            result = subprocess.run(
                ['sshpass', '-p', SSH_PASSWORD, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{SSH_USERNAME}@{ip_address}', 
                 'systemctl', 'is-active', '--quiet', service],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            service_status[service] = "active" if result.returncode == 0 else "inactive"
        pi_service_statuses[hostname] = service_status
    except Exception as e:
        print(f"Error requesting service status for {hostname}: {e}")

@app.route('/service_status', methods=['POST'])
def service_status_update():
    """ Endpoint to receive service status updates from Raspberry Pis """
    data = request.get_json()
    hostname = data['hostname']
    service_statuses = data['status']

    # Update global pi_service_statuses with the new status
    pi_service_statuses[hostname] = service_statuses
    return jsonify({"message": "Status updated successfully!"}), 200
if romy == False:
    turn_on_api()
    start_scripts()
@app.route('/create_room_template')
def create_room_template():
    return render_template('create_room.html')
@app.route('/create_room', methods=['POST'])
def create_room():
    if request.method == 'POST':
        name = request.form['name']
        create_html_file(name)
        create_room_folder(name)
        return f'HTML file "{name}.html" has been created in the templates folder.'
@app.route('/')
def index():
    # Get a list of all HTML files in the 'rooms' folder
    escape_rooms = [file.split('.')[0] for file in os.listdir('templates/rooms') if file.endswith('.html')]
    print(escape_rooms)
    return render_template('index.html', escape_rooms=escape_rooms)
@app.route('/rooms/<room>')
def room(room):
    return render_template(f'rooms/{room}.html')

@app.route('/get_rules/<room>', methods=['GET'])
def get_rules(room):
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            rules = json.load(file)
            #print(rules)
        return jsonify(rules)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])

@app.route('/add_rule/<room>', methods=['POST'])
def add_rule(room):
    new_rule = request.get_json()
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            rules = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        rules = []

    rules.append(new_rule)

    with open(f'json/{room}/rules.json', 'w') as file:
        json.dump(rules, file, indent=4)

    return jsonify({'message': 'Rule added successfully'})

@app.route('/update_rule/<room>', methods=['POST'])
def update_rule(room):
    print("Updating rule")
    if request.is_json:
        updated_rule = request.get_json()
        try:
            with open(f'json/{room}/rules.json', 'w') as file:
                rules = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify({'message': 'Error updating rule'})

        for rule in rules:
            if rule['sensor_name'] == updated_rule['sensor_name'] and rule['sensor_state'] == updated_rule['sensor_state']:
                rule.update(updated_rule)
                break

        with open(f'json/{room}/rules.json', 'w') as file:
            json.dump(rules, file, indent=4)

        return jsonify({'message': 'Rule updated successfully'})
    else:
        return jsonify({'message': 'Unsupported Media Type'}), 415

@app.route('/delete_rule/<room>', methods=['POST'])
def delete_rule(room):
    rule_to_delete = request.get_json()
    try:
        with open(f'json/{room}/rules.json', 'r') as file:
            rules = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error deleting rule'})

    rules = [rule for rule in rules if not (rule['sensor_name'] == rule_to_delete['sensor_name'] and rule['sensor_state'] == rule_to_delete['sensor_state'])]

    with open(f'json/{room}/rules.json', 'w') as file:
        json.dump(rules, file, indent=4)

    return jsonify({'message': 'Rule deleted successfully'})
@app.route('/rules/<room>')
def manage_rules(room):
    return render_template('rules.html', room=room)

@app.route('/get_sensors/<room>', methods=['GET'])
def get_sensors(room):
    try:
        with open(f'json/{room}/sensor_data.json', 'r') as file:
            sensors = json.load(file)
        return jsonify(sensors)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])

@app.route('/get_tasks/<room>', methods=['GET'])
def get_tasks(room):
    try:
        with open(f'json/{room}/tasks.json', 'r') as file:
            tasks = json.load(file)
        return jsonify(tasks)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])
@app.route('/save_rules/<room>', methods=['POST'])
def save_rules(room):
    data = request.get_json()
    room_dir = os.path.join('json', room)
    os.makedirs(room_dir, exist_ok=True)
    with open(os.path.join(room_dir, 'rules.json'), 'w') as f:
        json.dump(data, f, indent=4)
    return jsonify({"message": "Rules saved successfully!"})
@app.route('/save_states/<room>', methods=['POST'])
def save_states(room):
    data = request.get_json()
    room_dir = os.path.join('json', room)
    os.makedirs(room_dir, exist_ok=True)
    with open(os.path.join(room_dir, 'sensor_data.json'), 'w') as f:
        json.dump(data, f, indent=4)
    return jsonify({"message": "States saved successfully!"})
@app.route('/get_raspberry_pis/<room>', methods=['GET'])
def get_raspberry_pis(room):
    try:
        with open(f'json/{room}/raspberry_pis.json', 'r') as file:
            pis = json.load(file)
        return jsonify(pis)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])
@app.route('/save_raspberry_pis/<room>', methods=['POST'])
def save_raspberry_pis(room):
    data = request.get_json()
    room_dir = os.path.join('json', room)
    os.makedirs(room_dir, exist_ok=True)
    with open(os.path.join(room_dir, 'raspberry_pis.json'), 'w') as f:
        json.dump(data, f, indent=4)
    return jsonify({"message": "Raspberry Pis saved successfully!"})

@app.route('/get_sounds', methods=['GET'])
def get_sounds():
    sound_folder = os.path.join(app.static_folder, 'Music')
    sounds = [f for f in os.listdir(sound_folder) if f.endswith('.ogg')]
    return jsonify(sounds)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_interrupt)
    socketio.run(app, host='0.0.0.0', port=80, allow_unsafe_werkzeug=True)