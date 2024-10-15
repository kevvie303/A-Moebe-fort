from flask import Flask, render_template, request, redirect, jsonify, url_for, send_from_directory, send_file, after_this_request, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
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
from datetime import datetime, date
from youtube_downloader import download_video, convert_to_ogg
from html_creator import create_html_file, create_room_folder
from functools import partial
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
player_type = None
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
CHECKLIST_FILE = 'checklist_data.json'
#logging.basicConfig(level=logging.DEBUG)  # Use appropriate log level
active_ssh_connections = {}
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
broker_ip = "192.168.0.103"  # IP address of the broker Raspberry Pi
#broker_ip = "192.168.1.50"
# Define the topic prefix to subscribe to (e.g., "sensor_state/")
prefix_to_subscribe = "state_data/"
sensor_states = {}
# Callback function to process incoming MQTT messages

pi_service_statuses = {}  # New dictionary to store service statuses for each Pi
twinkle_sequence = ["g", "g", "d", "d", "e", "e", "d"]
current_sequence = []
def handle_rules(sensor_name, sensor_state, room):
    global sequence, code1, code2, code3, code4, code5, codesCorrect, current_sequence, twinkle_sequence, first_potion_solvable, second_potion_solvable, third_potion_solvable, fourth_potion_solvable
    if get_game_status(room) == {'status': 'playing'}:
        if check_rule("green_house_ir", room) and sequence == 0:
            task_state = check_task_state("tree-lights", room)
            if task_state == "pending":
                call_control_maglock_retriever("green-led", "unlocked")
                print("1")
                sequence = 1
        if check_rule("red_house_ir", room) and sequence == 1:
            task_state = check_task_state("tree-lights", room)
            if task_state == "pending":
                call_control_maglock_retriever("red-led", "unlocked")
                print("2")
                sequence = 2
        elif check_rule("red_house_ir", room) and sequence <= 0:
            task_state = check_task_state("tree-lights", room)
            if task_state == "pending":
                call_control_maglock_retriever("red-led", "unlocked")
                time.sleep(0.5)
                call_control_maglock_retriever("green-led", "locked")
                call_control_maglock_retriever("red-led", "locked")
                sequence = 0
        if check_rule("blue_house_ir", room) and sequence == 2:
            task_state = check_task_state("tree-lights", room)
            if task_state == "pending":
                solve_task("tree-lights", room)
        elif check_rule("blue_house_ir", room) and sequence != 2:
            task_state = check_task_state("tree-lights", room)
            if task_state == "pending":
                call_control_maglock_retriever("green-led", "unlocked")
                time.sleep(0.5)
                call_control_maglock_retriever("red-led", "locked")
                call_control_maglock_retriever("green-led", "locked")
                call_control_maglock_retriever("blue-led", "locked")
                sequence = 0
        if check_rule("moon-puzzle", room):
            task_state = check_task_state("moon-place", room)
            if task_state == "pending":
                solve_task("moon-place", room)
        if check_rule("flask-sensor", room):
            task_state = check_task_state("flask-place", room)
            if task_state == "pending":
                solve_task("flask-place", room)
        if check_rule("barrel-sensor", room):
            task_state = check_task_state("barrel-place", room)
            if task_state == "pending":
                solve_task("barrel-place", room)
        if check_rule("telescope-sensor", room):
            task_state = check_task_state("telescope-place", room)
            if task_state == "pending":
                solve_task("telescope-place", room)
        if check_rule("watersensor", room):
            task_state = check_task_state("plant-water", room)
            if task_state == "pending":
                solve_task("plant-water", room) 
        if sensor_name == "light_count":
            if sensor_state == "5":
                solve_task("lights-on", room)
        if sensor_name == "knocker":
            if sensor_state == "solved":
                solve_task("knocker-solve", room)
        if sensor_name == "webcam":
            if sensor_state == "solved":
                solve_task("camera-puzzle", room)
    if get_game_status(room) == {'status': 'playing'}:
        if sensor_name == "knocker":
            if sensor_state == "solved":
                solve_task("knocker-solve", room)
        if check_rule("ir-plant-1", room) and check_rule("ir-plant-5", room) and check_rule("ir-plant-8", room):
            task_state = check_task_state("green-potion", room)
            if task_state == "pending":
                publish.single("led/control/mlv-herbalist", "green", hostname=broker_ip)
                call_control_maglock_moonlight("humidifier", "unlocked")
                first_potion_solvable = True
                second_potion_solvable = False
                third_potion_solvable = False
                fourth_potion_solvable = False
        if check_rule("ir-plant-2", room) and check_rule("ir-plant-4", room) and check_rule("ir-plant-7", room):
            task_state = check_task_state("pink-potion", room)
            if task_state == "pending":
                publish.single("led/control/mlv-herbalist", "pink", hostname=broker_ip)
                call_control_maglock_moonlight("humidifier", "unlocked")
                second_potion_solvable = True
                first_potion_solvable = False
                third_potion_solvable = False
                fourth_potion_solvable = False
        if check_rule("ir-plant-3", room) and check_rule("ir-plant-6", room) and check_rule("ir-plant-9", room):
            task_state = check_task_state("yellow-potion", room)
            if task_state == "pending":
                publish.single("led/control/mlv-herbalist", "yellow", hostname=broker_ip)
                call_control_maglock_moonlight("humidifier", "unlocked")
                third_potion_solvable = True
                first_potion_solvable = False
                second_potion_solvable = False
                fourth_potion_solvable = False
        if check_rule("ir-plant-2", room) and check_rule("ir-plant-8", room) and check_rule("ir-plant-3", room):
            task_state = check_task_state("purple-potion", room)
            if task_state == "pending":
                publish.single("led/control/mlv-herbalist", "purple", hostname=broker_ip)
                call_control_maglock_moonlight("humidifier", "unlocked")
                fourth_potion_solvable = True
                first_potion_solvable = False
                second_potion_solvable = False
                third_potion_solvable = False
        if first_potion_solvable and sensor_name == "flask-rfid-1":
            if sensor_state == "584197941325":
                solve_task("green-potion", room)
                first_potion_solvable = False
        if second_potion_solvable and sensor_name == "flask-rfid-2":
            if sensor_state == "584196892797":
                solve_task("pink-potion", room)
                second_potion_solvable = False
        if third_potion_solvable and sensor_name == "flask-rfid-3":
            if sensor_state == "584196958334":
                solve_task("yellow-potion", room)
                third_potion_solvable = False
        if fourth_potion_solvable and sensor_name == "flask-rfid-4":
            if sensor_state == "584197875788":
                solve_task("purple-potion", room)
                fourth_potion_solvable = False
        # Check for ast-button-1 through ast-button-9 and match to notes
        button_note_map = {
            "ast-button-1": "a",
            "ast-button-2": "b",
            "ast-button-3": "c",
            "ast-button-4": "d",
            "ast-button-5": "e",
            "ast-button-6": "f",
            "ast-button-7": "g",
            "ast-button-8": "g-high",
            "ast-button-9": "twinkle"  # Extra button for resetting
        }

        if check_rule(sensor_name, room) and sensor_name in button_note_map:
            note = button_note_map[sensor_name]

            # Play the corresponding audio for the note
            publish.single(f"audio_control/mlv-astronomy/play", f"{note}.ogg", hostname=broker_ip)

            # Check if the button press is part of the sequence
            if note != "twinkle":  # Only check notes, not the reset button
                current_sequence.append(note)

                # Check if the sequence matches the beginning of twinkle_sequence
                if current_sequence == twinkle_sequence[:len(current_sequence)]:
                    if len(current_sequence) == len(twinkle_sequence):
                        # Sequence complete, solve the task
                        solve_task("planets", room)
                        print("Twinkle twinkle sequence completed! Solved planets.")
                        current_sequence = []  # Reset the sequence after solving
                else:
                    # Sequence is incorrect, reset
                    
                    print("Incorrect sequence. Resetting.")
                    current_sequence = []
                    call_control_maglock_moonlight("rem-lamp", "locked")
                    time.sleep(0.5)
                    call_control_maglock_moonlight("rem-lamp", "unlocked")
                    time.sleep(0.5)
                    call_control_maglock_moonlight("rem-lamp", "locked")
                    time.sleep(0.5)
                    call_control_maglock_moonlight("rem-lamp", "unlocked")
                    time.sleep(0.5)
                    call_control_maglock_moonlight("rem-lamp", "locked")

            # If the twinkle button is pressed, reset the sequence
            elif note == "twinkle":
                print("Reset button pressed. Sequence reset.")
                current_sequence = []
                call_control_maglock_moonlight("rem-lamp", "locked")
        if sensor_name == "keypad":
            sensor_state_int = int(sensor_state)
            print(sensor_state)
            if sensor_state == "1528" and not code1:
                code1 = True
                solve_task("flowers", room)
            elif (sensor_state == "7867" or sensor_state == "8978") and not code2:
                code2 = True
                solve_task("kite-count", room)
            elif sensor_state == "0128" and not code3:
                code3 = True
                solve_task("number-feel", room)
            elif sensor_state == "5038" and not code4:
                code4 = True
                solve_task("fence-decrypt", room)
            else:
                call_control_maglock_retriever("red-led-keypad", "unlocked")
                time.sleep(1)
                call_control_maglock_retriever("red-led-keypad", "locked")
            if sensor_name == "laser":
                print(sensor_state)
                if sensor_state == "100":
                    solve_task("laser-game")
                    publish.single("servo_control/ret-middle", "servo1", hostname=broker_ip)
                    call_control_maglock_retriever("laser-1", "unlocked")
                    call_control_maglock_retriever("laser-2", "unlocked")
                if sensor_state == "50":
                    publish.single("servo_control/ret-middle", "servo2", hostname=broker_ip)
                    call_control_maglock_retriever("laser-2", "unlocked")
                    call_control_maglock_retriever("laser-1", "locked")
# Function to handle incoming MQTT messages
def on_message(client, userdata, message):
    global sensor_states, pi_service_statuses, code1, code2, code3, code4, code5, codesCorrect, sequence
    
    # Extract the topic and message payload
    topic = message.topic
    parts = topic.split("/")
    print(parts)
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
        print(room)
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
        print(f"Locking action executed successfully for task: {task}, isChecked: {is_checked}")
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
            item_name = item.get("name", "")

            # Special condition for IR sensors
            if item_type == "Sensor" and "ir" in item_name.lower():
                if item["state"] == "Not Triggered":
                    return True
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
    return "Volume faded successfully"
@app.route('/fade_music_out/<room>', methods=['POST'])
def fade_music_out_hint(room):
        # Gradually reduce the volume from 80 to 40
    for volume in range(35, 10, -1):
        # Send the volume command to the Raspberry Pi
        
        if check_task_state("squeekuence", room) == "solved":
            publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
        else:
            publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
        
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
    time.sleep(1)
    publish.single("audio_control/all_retriever/play", "prehint.ogg", hostname=broker_ip)
    return "Volume faded successfully"
@app.route('/fade_music_in/<room>', methods=['POST'])
def fade_music_in(room):
        # Gradually reduce the volume from 80 to 40
    for volume in range(10, 35, 1):
        # Send the volume command to the Raspberry Pi
        if check_task_state("squeekuence", room) == "solved":
            publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
        else:
            publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
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
    file_path = os.path.join('json', room, 'tasks.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                tasks = json.load(file)

            # Map task states for easy lookup
            task_states = {task['task']: task['state'] for task in tasks}

            for task in tasks:
                # Check if task has dependencies
                if 'depends_on' in task:
                    dependencies = task['depends_on']
                    # Check if all dependencies are solved
                    if all(task_states.get(dep) in ['solved', 'skipped'] for dep in dependencies):
                        task['blocked'] = False
                    else:
                        task['blocked'] = True
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
    file_path = os.path.join('json', room, 'tasks.json')
    game_status = get_game_status(room)
    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)
        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'solved'
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)
        socketio.emit('task_update', room="all_clients")
        if task_name == "lights-on":
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/mlv-central/play", "bg_central.ogg", hostname=broker_ip)
                publish.single("audio_control/raspberrypi/volume", "5 bg_corridor.ogg", hostname=broker_ip)
        elif task_name == "moon-place":
            if game_status == {'status': 'playing'}:
                call_control_maglock_moonlight("astronomy-door-lock", "locked")
                publish.single("led/control/mlv-astronomy", "unlocked", hostname=broker_ip)
                publish.single("audio_control/mlv-central/play", "right door.ogg", hostname=broker_ip)
        elif task_name == "knocker-solve":
            if game_status == {'status': 'playing'}:
                call_control_maglock_moonlight("tavern-door-lock", "locked")
                publish.single("led/control/mlv-tavern", "unlocked", hostname=broker_ip)
        elif task_name == "planets":
            if game_status == {'status': 'playing'}:
                call_control_maglock_moonlight("rem-lamp", "unlocked")
                call_control_maglock_moonlight("blacklight-astronomy", "unlocked")
                publish.single("led/control/mlv-astronomy", "locked", hostname=broker_ip)
                publish.single("audio_control/mlv-central/play", "planet-solve.ogg", hostname=broker_ip)
        elif task_name == "constellations":
            if game_status == {'status': 'playing'}:
                call_control_maglock_moonlight("blacklight-astronomy", "locked")
        elif task_name == "camera-puzzle":
            if game_status == {'status': 'playing'}:
                print("camera puzzle solved")
        elif task_name == "green-potion":
            if game_status == {'status': 'playing'}:
                publish.single("led/control/mlv-herbalist", "cauldron-off", hostname=broker_ip)
                potion_count += 1
                call_control_maglock_moonlight("humidifier", "locked")
                if potion_count == 4:
                    solve_task("potion-all", room)
        elif task_name == "pink-potion":
            if game_status == {'status': 'playing'}:
                publish.single("led/control/mlv-herbalist", "cauldron-off", hostname=broker_ip)
                potion_count += 1
                call_control_maglock_moonlight("humidifier", "locked")
                if potion_count == 4:
                    solve_task("potion-all", room)
        elif task_name == "yellow-potion":
            if game_status == {'status': 'playing'}:
                publish.single("led/control/mlv-herbalist", "cauldron-off", hostname=broker_ip)
                potion_count += 1
                call_control_maglock_moonlight("humidifier", "locked")
                if potion_count == 4:
                    solve_task("potion-all", room)
        elif task_name == "purple-potion":
            if game_status == {'status': 'playing'}:
                publish.single("led/control/mlv-herbalist", "cauldron-off", hostname=broker_ip)
                potion_count += 1
                call_control_maglock_moonlight("humidifier", "locked")
                if potion_count == 4:
                    solve_task("potion-all", room)
        elif task_name == "plant-water":
            if game_status == {'status': 'playing'}:
                call_control_maglock_moonlight("herbalist-door-lock", "locked")
        elif task_name == "sigil-all":
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/mlv-central/play", "sigal-all-first.ogg", hostname=broker_ip)
                publish.single("audio_control/mlv-central/volume", "100 sigal-all-first.ogg", hostname=broker_ip)
                publish.single("audio_control/mlv-central/volume", "20 bg_central.ogg", hostname=broker_ip)
                time.sleep(12)
                publish.single("audio_control/mlv-central/play", "sigil-all-second.ogg", hostname=broker_ip)
                publish.single("audio_control/mlv-central/volume", "100 sigil-all-second.ogg", hostname=broker_ip)
                time.sleep(13)
                send_dmx_command(0, 0, 0, 0, 255)
                time.sleep(5)
                send_dmx_command(0, 0, 0, 0, 0)
                call_control_maglock_moonlight("lamp-post-1", "locked")
                call_control_maglock_moonlight("lamp-post-2", "locked")
                publish.single("audio_control/all_moonlight/full_stop", "stop", hostname=broker_ip)
                publish.single("audio_control/mlv-central/play", "tense.ogg", hostname=broker_ip)
                publish.single("audio_control/mlv-central/volume", "150 tense.ogg", hostname=broker_ip)
                start_sequence()
        elif task_name == "paw-maze":
            if squeak_job == False:
                scheduler.add_job(start_squeak, 'interval', seconds=30, id='squeakjob')
                squeak_job = True
            publish.single("audio_control/ret-top/play", "squeek.ogg", hostname=broker_ip)
        elif task_name == "laser-game":
            publish.single("actuator/control/ret-laser", "100", hostname=broker_ip)
        elif task_name == "woef-woef":
            if game_status == {'status': 'playing'}:
                if bird_job == True:
                    scheduler.remove_job('birdjob')
                    bird_job = False
                publish.single("audio_control/ret-top/play", "hok.ogg", hostname=broker_ip)
                call_control_maglock_retriever("doghouse-lock", "locked")
        elif task_name == "squeekuence":
            if game_status == {'status': 'playing'}:
                call_control_maglock_retriever("lab-hatch-lock", "locked")
                call_control_maglock_retriever("laser-2", "locked")
                time.sleep(4)
                publish.single("audio_control/ret-middle/play", "Background.ogg", hostname=broker_ip)
                fade_music_in(room)
                publish.single("audio_control/ret-top/volume", "3 Ambience.ogg", hostname=broker_ip)
            if squeak_job == True:
                scheduler.remove_job('squeakjob')
                squeak_job = False
        elif task_name == "flowers":
            code1 = True
            codesCorrect += 1
            call_control_maglock_retriever("green-led-keypad", "locked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience", room)
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "bloemen.ogg", hostname=broker_ip)
            call_control_maglock_retriever("green-led-keypad", "locked")
            time.sleep(10)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in(room)
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in(room)
        elif task_name == "kite-count":
            code2 = True
            codesCorrect += 1
            call_control_maglock_retriever("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience", room)
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "vlieger.ogg", hostname=broker_ip)
            call_control_maglock_retriever("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in(room)
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in(room)
        elif task_name == "number-feel":
            code3 = True
            codesCorrect += 1
            call_control_maglock_retriever("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience", room)
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "plantenbak.ogg", hostname=broker_ip)
            call_control_maglock_retriever("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in(room)
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in(room)
        elif task_name == "fence-decrypt":
            code4 = True
            codesCorrect += 1
            call_control_maglock_retriever("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience", room)
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "hek.ogg", hostname=broker_ip)
            call_control_maglock_retriever("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in(room)
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in(room)
        elif task_name == "sinus-game":
            print("nothing yet")
        elif task_name == "squid-game":
            if game_status == {'status': 'playing'}:
                call_control_maglock_retriever("top_left_light", "unlocked")
                call_control_maglock_retriever("top_right_light", "unlocked")
                call_control_maglock_retriever("bottom_left_light", "unlocked")
                call_control_maglock_retriever("bottom_right_light", "unlocked")
                publish.single("audio_control/ret-middle/play", "gelukt.ogg", hostname=broker_ip)
                time.sleep(3)
                call_control_maglock_retriever("sliding-door-lock", "locked")
                time.sleep(6)
                if should_balls_drop == True:
                    call_control_maglock_retriever("ball-drop-lock", "locked")
                publish.single("audio_control/ret-middle/stop", "Background.ogg", hostname=broker_ip)
                publish.single("audio_control/ret-middle/play", "Dogsout.ogg", hostname=broker_ip)
        elif task_name == "tree-lights":
            if bird_job == True:
                scheduler.remove_job('birdjob')
                bird_job = False
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/all_retriever/play", "correct-effect.ogg", hostname=broker_ip)
                time.sleep(1)
                code5 = True
                print("3")
                call_control_maglock_retriever("blue-led", "unlocked")
                fade_out_thread = threading.Thread(target=fade_music_out("Ambience", room))
                fade_out_thread.start()
                time.sleep(1)
                call_control_maglock_retriever("blue-led", "locked")
                call_control_maglock_retriever("green-led", "locked")
                call_control_maglock_retriever("red-led", "locked")
                time.sleep(1)
                call_control_maglock_retriever("green-led", "unlocked")
                call_control_maglock_retriever("red-led", "unlocked")
                call_control_maglock_retriever("blue-led", "unlocked")
                time.sleep(1)
                call_control_maglock_retriever("green-led", "locked")
                call_control_maglock_retriever("red-led", "locked")
                call_control_maglock_retriever("blue-led", "locked")
                time.sleep(1)
                call_control_maglock_retriever("green-led", "unlocked")
                call_control_maglock_retriever("red-led", "unlocked")
                call_control_maglock_retriever("blue-led", "unlocked")
                time.sleep(1)
                call_control_maglock_retriever("green-led", "locked")
                call_control_maglock_retriever("red-led", "locked")
                call_control_maglock_retriever("blue-led", "locked")
                sequence = 0
                time.sleep(1)
                publish.single("audio_control/ret-top/play", "boom.ogg", hostname=broker_ip)
                time.sleep(7)
                if code1 and code2 and code3 and code4 and code5:
                    print("executed")
                    time.sleep(7)
                    publish.single("audio_control/ret-top/play", "schuur_open.ogg", hostname=broker_ip)
                    time.sleep(5)
                    fade_music_in(room)
                    call_control_maglock_retriever("shed-door-lock", "locked")
                    code1 = False
                    code2 = False
                    code3 = False
                    code4 = False
                    code5 = False
                else:
                    fade_in_thread = threading.Thread(target=fade_music_in(room))
                    fade_in_thread.start()
        if code1 and code2 and code3 and code4 and code5:
            print("executed")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "schuur_open.ogg", hostname=broker_ip)
            time.sleep(5)
            fade_music_in(room)
            call_control_maglock_retriever("shed-door-lock", "locked")
            code1 = False
            code2 = False
            code3 = False
            code4 = False
            code5 = False
        if codesCorrect == 2:
            print("TRIGGERED")
            codesCorrect += 1
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "goed_bezig.ogg", hostname=broker_ip)
            time.sleep(6)
            fade_music_in(room)
        if codesCorrect == 1 and should_hint_shed_play == True:
            should_hint_shed_play = False
            print("TRIGGERED")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "after1code.ogg", hostname=broker_ip)
            time.sleep(4)
            fade_music_in(room)
        if game_status == {'status': 'playing'}:
            if task_name == "barrel-place":
                sigil_count += 1
                publish.single("led/control/mlv-webcam", "1/3", hostname=broker_ip)
                if sigil_count == 3:
                    solve_task("sigil-all", room)
            if task_name == "flask-place":
                sigil_count += 1
                publish.single("led/control/mlv-webcam", "1/3", hostname=broker_ip)
                if sigil_count == 3:
                    solve_task("sigil-all", room)
            if task_name == "telescope-place":
                sigil_count += 1
                publish.single("led/control/mlv-webcam", "1/3", hostname=broker_ip)
                if sigil_count == 3:
                    solve_task("sigil-all", room)
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
def sequence_thread():
    global sequence_running
    try:
        sequence_duration = 0.03  # seconds per step
        steps_between_points = 50  # Adjust this for smoother transitions
        publish.single(TOPIC_TAVERN, "blink_red", hostname=broker_ip)
        publish.single(TOPIC_HERBALIST, "blink_green", hostname=broker_ip)
        publish.single(TOPIC_ASTRONOMY, "blink_green", hostname=broker_ip)
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
                publish.single(TOPIC_TAVERN, "blink_green", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_red", hostname=broker_ip)
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
                publish.single(TOPIC_TAVERN, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_green", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_red", hostname=broker_ip)
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
                publish.single(TOPIC_TAVERN, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_green", hostname=broker_ip)
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
                publish.single(TOPIC_TAVERN, "blink_red", hostname=broker_ip)
                publish.single(TOPIC_HERBALIST, "blink_green", hostname=broker_ip)
                publish.single(TOPIC_ASTRONOMY, "blink_green", hostname=broker_ip)
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
                if device["name"] == "laser-1" or device["name"] == "laser-2":
                    call_control_maglock_retriever(device["name"], "unlocked")
        else:
            for device in devices:
                if device["type"] in ["maglock", "light"]:
                    call_control_maglock_moonlight(device["name"], "locked")
            publish.single("led/control/mlv-herbalist", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-tavern", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-astronomy", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-corridors", "locked", hostname=broker_ip)
            publish.single("led/control/mlv-webcam", "locked", hostname=broker_ip)
        return "Room snoozed"
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
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
    
@app.route('/get_tasks/<room>', methods=['GET'])
def get_tasks(room):
    file_path = os.path.join('json', room, 'tasks.json')
    
    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)
        return jsonify(tasks)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])
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
            send_dmx_command(preset['pan'], preset['tilt'], preset['colour'], preset['gobo'], preset['smoke'])
@app.route('/play_music/<room>', methods=['POST'])
def play_music(room):
    data = request.json
    message = data.get('message')
    print(message)
    if message == "laser-game-1":
        publish.single("actuator/control/ret-laser", "50", hostname=broker_ip)
        publish.single("servo_control/ret-middle", "servo2", hostname=broker_ip)
        call_control_maglock_retriever("laser-2", "unlocked")
        call_control_maglock_retriever("laser-1", "locked")
    elif message == "knocker-solve-1":
        handle_preset("knocker-solve")
    elif message == "moon-place-1":
        handle_preset("moon-place")
    elif message == "plant-place-1":
        handle_preset("plant-place")
    elif room == "The Retriever":
        publish.single("audio_control/all_retriever/play", message, hostname=broker_ip)
    else:
        publish.single("audio_control/all_moonlight/play", message, hostname=broker_ip)
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
            if "green-led" in maglock or "red-led" in maglock or "blue-led" in maglock:
                print(maglock)
                # Reverse the action for this specific case
                action = 'locked' if action == 'unlocked' else 'unlocked'
            # Publish the MQTT message with the appropriate Pi's name
            mqtt_message = f"{sensor['pin']} {action}"
            publish.single(f"actuator/control/{pi_name}", mqtt_message, hostname=broker_ip)
            return "done"
        elif sensor['name'] == maglock and sensor['type'] == 'led':
            pi_name = sensor['pi']
            print(sensor)
            print(pi_name)
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
    #print(maglock)
    #print(action)
    #print(room)
    sensor_data = read_sensor_data2(room)
    for sensor in sensor_data:
        if sensor['name'] == maglock and (sensor['type'] == 'maglock' or sensor['type'] == 'light'):
            pi_name = sensor['pi']
            if "green-led" in maglock or "red-led" in maglock or "blue-led" in maglock:
                #print(maglock)
                # Reverse the action for this specific case
                action = 'locked' if action == 'unlocked' else 'unlocked'
            # Publish the MQTT message with the appropriate Pi's name
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
@app.route('/timer/start/<room>', methods=['POST'])
def start_timer(room):
    global timer_value, speed, timer_running, timer_thread, start_time, bird_job

    # Start a new timer thread for the room if not already running
    if room not in timer_threads or not timer_threads[room].is_alive():
        speed[room] = 1  # Reset timer speed to 1
        timer_values[room] = 3600  # Reset timer value to 60 minutes
        write_timer_value(timer_values[room], room)
        timer_running[room] = True
        timer_threads[room] = Thread(target=update_timer, args=(room,))
        timer_threads[room].daemon = True
        timer_threads[room].start()

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
def check_service_status(ip_address, service_name):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
    stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service_name}')
    status = stdout.read().decode().strip() == 'active'
    ssh.close()
    return status

def restart_service(ip_address, service_name):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
    ssh.exec_command(f'sudo systemctl restart {service_name}')
    ssh.close()

def get_raspberry_pis_with_prefix(prefix, scanner):
    pi_devices = scanner.scan_for_raspberrypi()
    pi_info = {hostname: {"ip_address": ip, "services": []} for ip, _, hostname in pi_devices if hostname and hostname.startswith(prefix)}
    return pi_info

def get_required_services():
    with open('json/raspberry_pis.json', 'r') as file:
        data = json.load(file)
    return {entry["hostname"]: entry.get("services", []) for entry in data}
pi_service_statuses = {}
preparedValue = {}
@app.route('/prepare/<room>', methods=['POST'])
def prepare_game(room):
    global client, pi_service_statuses, player_type, preparedValue, should_hint_shed_play, new_init_time
    new_init_time = 3600
    if room == "The Retriever":
        should_hint_shed_play = True
        prefix = "ret"
    else:
        prefix = "mlv"
    print(prefix)
    if get_game_status(room) == {'status': 'prepared'}:
        return jsonify({"message": preparedValue}), 200
    reset_prepare(room)
    # Assuming you have logic for preparing the game
    # Load Raspberry Pi configuration from JSON file
    with open(f'json/{room}/raspberry_pis.json', 'r') as file:
        pi_config = json.load(file)

    # Loop over each Raspberry Pi and request service statuses
    
    for pi in pi_config:
        if "services" in pi and pi["hostname"].startswith(prefix):
            hostname = pi["hostname"]
            services = pi["services"]
            print(services)
            print(hostname)
            client.publish(f"request_service_statuses/{hostname}", json.dumps({"services": services}))
    time.sleep(0.7)
    # Convert the service statuses to True if active, False if inactive
    converted_statuses = {}
    preparedValue = converted_statuses
    for pi, status_dict in pi_service_statuses.items():
        converted_statuses[pi] = {service: status == "active" for service, status in status_dict.items()}
    player_type = request.form.get('playerType')
    # Return the converted service statuses
    print(converted_statuses)
    update_game_status("prepared", room)
    time.sleep(0.1)
    if room == "The Retriever":
        publish.single("audio_control/ret-top/play", "Lounge.ogg", hostname=broker_ip)
    else:
        publish.single("audio_control/raspberrypi/play", "bg_corridor.ogg", hostname=broker_ip)
        publish.single("led/control/mlv-corridors", "unlocked", hostname=broker_ip)
    return jsonify({"message": converted_statuses}), 200
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
if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_interrupt)
    socketio.run(app, host='0.0.0.0', port=80, allow_unsafe_werkzeug=True)