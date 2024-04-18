from flask import Flask, render_template, request, redirect, jsonify, url_for, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import json
import paramiko
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
import threading
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from networkscanner import NetworkScanner
from datetime import datetime, date
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
CHECKLIST_FILE = 'json/checklist_data.json'
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

@app.route('/check_devices_status', methods=['GET'])
def check_devices_status():
    try:
        with open('json/raspberry_pis.json', 'r') as file:
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

#broker_ip = "192.168.0.103"  # IP address of the broker Raspberry Pi
broker_ip = "192.168.1.13"
# Define the topic prefix to subscribe to (e.g., "sensor_state/")
prefix_to_subscribe = "state_data/"
sensor_states = {}
# Callback function to process incoming MQTT messages

pi_service_statuses = {}  # New dictionary to store service statuses for each Pi

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
        sensor_state = message.payload.decode("utf-8")
        sensor_states[sensor_name] = sensor_state
        print(f"Received MQTT message - Sensor: {sensor_name}, State: {sensor_state}")

        if sensor_name in sensor_states:
            sensor_states[sensor_name] = sensor_state
            update_json_file()
            socketio.emit('sensor_update', room="all_clients")
            print("State changed. Updated JSON.")
        #print(sensor_states)
        if get_game_status() == {'status': 'playing'}:
            global sequence
            if check_rule("green_house_ir") and sequence == 0:
                task_state = check_task_state("tree-lights")
                if task_state == "pending":
                    call_control_maglock("green-led", "unlocked")
                    print("1")
                    sequence = 1
            if check_rule("red_house_ir") and sequence == 1:
                task_state = check_task_state("tree-lights")
                if task_state == "pending":
                    call_control_maglock("red-led", "unlocked")
                    print("2")
                    sequence = 2
            elif check_rule("red_house_ir") and sequence <= 0:
                task_state = check_task_state("tree-lights")
                if task_state == "pending":
                    call_control_maglock("red-led", "unlocked")
                    time.sleep(0.5)
                    call_control_maglock("green-led", "locked")
                    call_control_maglock("red-led", "locked")
                    sequence = 0
            if check_rule("blue_house_ir") and sequence == 2:
                task_state = check_task_state("tree-lights")
                if task_state == "pending":
                    solve_task("tree-lights")
            elif check_rule("blue_house_ir") and sequence != 2:
                task_state = check_task_state("tree-lights")
                if task_state == "pending":
                    call_control_maglock("green-led", "unlocked")
                    time.sleep(0.5)
                    call_control_maglock("red-led", "locked")
                    call_control_maglock("green-led", "locked")
                    call_control_maglock("blue-led", "locked")
                    sequence = 0
            if sensor_name == "keypad":
                sensor_state_int = int(sensor_state)
                print(sensor_state)
                if sensor_state == "1528" and code1 == False:
                    code1 = True
                    solve_task("flowers")
                elif (sensor_state == "7867" or sensor_state =="8978") and code2 == False:
                    code2 = True
                    solve_task("kite-count")
                elif sensor_state == "0128" and code3 == False:
                    code3 = True
                    solve_task("number-feel")
                elif sensor_state == "5038" and code4 == False:
                    code4 = True
                    solve_task("fence-decrypt")
                else:
                    call_control_maglock("red-led-keypad", "unlocked")
                    time.sleep(1)
                    call_control_maglock("red-led-keypad", "locked")
                
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

        # Determine the action based on the isChecked flag
        action = "locked" if is_checked else "unlocked"
        execute_lock_command(task, action)

        # Update the checklist status
        update_checklist(task, is_checked)
        socketio.emit('checklist_update', {'task': task, 'isChecked': is_checked}, room="all_clients")
        print(f"Locking action executed successfully for task: {task}, isChecked: {is_checked}")
        return jsonify({'success': True, 'message': 'Locking action executed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def execute_lock_command(task, action):
    try:
        if task == "Doe de entree deur dicht":
            call_control_maglock("entrance-door-lock", action)
        if task == "Loop naar midden gang, sluit beide hekken.":
            call_control_maglock("iron-door-child", action)
            call_control_maglock("iron-door-adult", action)
        if task == "Leg personeelspas Mendez in onderste la links van bureau, sluit la.":
            call_control_maglock("bovenste-la-guard", action)
        if task == "Geheime deur dicht door aan ijzeren kabel te trekken.":
            call_control_maglock("secret-door-lock", action)
        if task == "Sleutel terughangen achter speaker.":
            call_control_maglock("key-drop-lock", action)
        
    except Exception as e:
        print(f"Error executing {action} command: {str(e)}")


def update_checklist(task, is_checked):
    try:
        # Read the current checklist data
        with open(CHECKLIST_FILE, 'r') as file:
            checklist_data = json.load(file)

        # Find the task in the checklist and update its completed status
        for item in checklist_data:
            if item['task'] == task:
                item['completed'] = is_checked

        # Write the updated data back to the file
        with open(CHECKLIST_FILE, 'w') as file:
            json.dump(checklist_data, file, indent=2)
    except Exception as e:
        print(f"Error updating checklist: {str(e)}")
@app.route('/get-checklist', methods=['GET'])
def get_checklist_route():
    try:
        checklist = get_checklist()
        return jsonify({'success': True, 'checklist': checklist})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def get_checklist():
    try:
        # Read the current checklist data
        with open(CHECKLIST_FILE, 'r') as file:
            checklist_data = json.load(file)

        return checklist_data
    except Exception as e:
        print(f"Error getting checklist: {str(e)}")
        return []
def check_task_state(task_name):
    json_file_path = 'json/tasks.json'  # Set the path to your JSON file
    with open(json_file_path, 'r') as json_file:
        task_data = json.load(json_file)

    for task in task_data:
        if task["task"] == task_name:
            return task["state"]
    return "Task not found"
def update_json_file():
    try:
        # Read existing JSON data
        with open("json/sensor_data.json", 'r') as json_file:
            sensor_data = json.load(json_file)

        # Update sensor states in the JSON data
        for sensor in sensor_data:
            sensor_name = sensor["name"]
            if sensor_name in sensor_states:
                sensor["state"] = sensor_states[sensor_name]

        # Write the updated JSON data back to the file
        with open("json/sensor_data.json", 'w') as json_file:
            json.dump(sensor_data, json_file, indent=4)

    except Exception as e:
        print(f"Error updating JSON file: {e}")
@app.route('/get_sensor_data', methods=['GET'])
def read_sensor_data():
    with open("json/sensor_data.json", "r") as file:
        sensor_data = json.load(file)
    return jsonify(sensor_data)
def read_sensor_data2():
    with open("json/sensor_data.json", "r") as file:
        sensor_data = json.load(file)
    return sensor_data
def check_rule(item_name):
    try:
        # Read sensor data from the JSON file
        with open("json/sensor_data.json", 'r') as json_file:
            state_data = json.load(json_file)

        # Find the sensor with the specified name
        item = next((i for i in state_data if i["name"] == item_name), None)

        if item:
            item_type = item.get("type")  # Default to "sensor" if type is not specified

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
#def check_rule(sensor_name):
    global sequence
    if sensor_name == 'green_house_ir' and sensor_states.get(sensor_name) == 'Triggered' and sequence == 0:
        pi3.exec_command("raspi-gpio set 15 op dh")
        print("1")
        sequence = 1
    if sensor_name == 'red_house_ir' and sensor_states.get(sensor_name) == 'Triggered' and sequence == 1:
        pi3.exec_command("raspi-gpio set 21 op dh")
        print("2")
        sequence = 2
    elif sensor_name == 'red_house_ir' and sensor_states.get(sensor_name) == 'Triggered' and sequence <= 0:
        pi3.exec_command("raspi-gpio set 21 op dh")
        time.sleep(0.5)
        pi3.exec_command("raspi-gpio set 21 op dl")
        pi3.exec_command("raspi-gpio set 15 op dl")
        sequence = 0
    if sensor_name == 'blue_house_ir' and sensor_states.get(sensor_name) == 'Triggered' and sequence == 2:
        solve_task("tree-lights")
        print("3")
        pi3.exec_command("raspi-gpio set 23 op dh")
        fade_out_thread = threading.Thread(target=fade_music_out)
        fade_out_thread.start()
        time.sleep(1)
        pi3.exec_command("raspi-gpio set 23 op dl \n raspi-gpio set 21 op dl \n raspi-gpio set 15 op dl")
        time.sleep(1)
        pi3.exec_command("raspi-gpio set 23 op dh \n raspi-gpio set 21 op dh \n raspi-gpio set 15 op dh")
        time.sleep(1)
        pi3.exec_command("raspi-gpio set 23 op dl \n raspi-gpio set 21 op dl \n raspi-gpio set 15 op dl")
        time.sleep(1)
        pi3.exec_command("raspi-gpio set 23 op dh \n raspi-gpio set 21 op dh \n raspi-gpio set 15 op dh")
        time.sleep(1)
        pi3.exec_command("raspi-gpio set 23 op dl \n raspi-gpio set 21 op dl \n raspi-gpio set 15 op dl")
        sequence = 0
        time.sleep(1)
        pi3.exec_command("mpg123 -a hw:0,0 Music/Tree-solve.mp3")
        time.sleep(7)
        fade_in_thread = threading.Thread(target=fade_music_in)
        fade_in_thread.start()
    elif sensor_name == 'blue_house_ir' and sensor_states.get(sensor_name) == 'Triggered' and sequence != 2:
        pi3.exec_command("raspi-gpio set 23 op dh")
        time.sleep(0.5)
        pi3.exec_command("raspi-gpio set 23 op dl")
        pi3.exec_command("raspi-gpio set 21 op dl")
        pi3.exec_command("raspi-gpio set 15 op dl")
        sequence = 0

    if sensor_name == 'top_left_kraken' and sensor_states.get(sensor_name) == 'Triggered':
        pi2.exec_command('raspi-gpio set 12 op dh')
    else:
        pi2.exec_command('raspi-gpio set 12 op dl')
    if sensor_name == 'bottom_left_kraken' and sensor_states.get(sensor_name) == 'Triggered':
        pi2.exec_command('raspi-gpio set 1 op dh')
    else:
        pi2.exec_command('raspi-gpio set 1 op dl')
    if sensor_name == 'top_right_kraken' and sensor_states.get(sensor_name) == 'Triggered':
        pi2.exec_command('raspi-gpio set 7 op dh')
    else:
        pi2.exec_command('raspi-gpio set 7 op dl')
    if sensor_name == 'bottom_right_kraken' and sensor_states.get(sensor_name) == 'Triggered':
        pi2.exec_command('raspi-gpio set 8 op dh')
    else:
        pi2.exec_command('raspi-gpio set 8 op dl')
# Create an MQTT client instance
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
    return render_template('pow.html')
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
    with open('json/raspberry_pis.json') as f:
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

@app.route('/pause_music', methods=['POST'])
def pause_music():
    selected_file = request.form['file']
    soundcard_channel = request.form['channel']  # Get the soundcard channel from the AJAX request
    if selected_file:
        # Fade out the music gradually
        fade_duration = 2  # Adjust the fade duration as needed
        fade_interval = 0.1  # Adjust the fade interval as needed
        max_volume = 25
                # Update the status in the JSON file to "paused"
        file_path = os.path.join(current_dir, 'json', 'file_status.json')
        with open(file_path, 'r') as file:
            file_data = json.load(file)

        for entry in file_data:
            if entry['filename'] == selected_file and entry['soundcard_channel'] == soundcard_channel:
                entry['status'] = 'paused'
                break
        for entry in file_data:
            if entry['filename'] == selected_file and entry['soundcard_channel'] == soundcard_channel:
                pi_name = entry['pi']
                break
        else:
            return 'Selected song not found in the JSON file'
        
        if pi_name == 'pi2':
            pi = pi2
        elif pi_name == 'pi3':
            pi = pi3
            max_volume = 85
        with open(file_path, 'w') as file:
            json.dump(file_data, file)
        # Calculate the step size for volume reduction
        step_size = max_volume / (fade_duration / fade_interval)
            # Extract the first number after "hw"
        import re
        match = re.search(r'hw:(\d+)', soundcard_channel)
        if match:
            soundcard_number = match.group(1)
        else:
            return 'Invalid soundcard channel'
        # Get the process ID of the mpg123 process
        command = f'pgrep -f "mpg123 -a {soundcard_channel} Music/{selected_file}"'
        stdin, stdout, stderr = pi.exec_command(command)
        process_id = stdout.read().decode().strip()

        if process_id:
            # Reduce the volume gradually
            for volume in reversed(range(0, max_volume, int(step_size))):
                command = f'amixer -c {soundcard_number} set PCM Playback Volume {volume}%'
                pi.exec_command(command)
                time.sleep(fade_interval)

                # Check if the volume reached 0 
                if volume <= 0:
                    # Pause the music by sending a SIGSTOP signal to the mpg123 process
                    command = f'pkill -STOP -f "mpg123 Music/{selected_file}"'
                    pi.exec_command(command)

            return f'Music paused for {selected_file} on {pi}'
        else:
            return f'{selected_file} is not currently playing'
    else:
        return 'No file selected to pause'
def fade_music_out(file):
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
        publish.single("audio_control/all/play", "prehint.ogg", hostname=broker_ip)
    return "Volume faded successfully"
@app.route('/fade_music_out', methods=['POST'])
def fade_music_out_hint():
        # Gradually reduce the volume from 80 to 40
    for volume in range(35, 10, -1):
        # Send the volume command to the Raspberry Pi
        
        if check_task_state("squeekuence") == "solved":
            publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
        else:
            publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
        
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
    time.sleep(1)
    publish.single("audio_control/all/play", "prehint.ogg", hostname=broker_ip)
    return "Volume faded successfully"
@app.route('/fade_music_in', methods=['POST'])
def fade_music_in():
        # Gradually reduce the volume from 80 to 40
    for volume in range(10, 35, 1):
        # Send the volume command to the Raspberry Pi
        if check_task_state("squeekuence") == "solved":
            publish.single("audio_control/ret-middle/volume", f"{volume} Background.ogg", hostname=broker_ip)
        else:
            publish.single("audio_control/ret-top/volume", f"{volume} Ambience.ogg", hostname=broker_ip)
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
    return "Volume faded successfully"
@app.route('/resume_music', methods=['POST'])
def resume_music():
    selected_file = request.form['file']
    soundcard_channel = request.form['channel']
    if selected_file:
        # Fade in the music gradually
        fade_duration = 2  # Adjust the fade duration as needed
        fade_interval = 0.1  # Adjust the fade interval as needed
        target_volume = 25  # Adjust the desired volume level
        file_path = os.path.join(current_dir, 'json', 'file_status.json')
        with open(file_path, 'r') as file:
            file_data = json.load(file)

        for entry in file_data:
            if entry['filename'] == selected_file and entry['soundcard_channel'] == soundcard_channel:
                entry['status'] = 'playing'
                break
        for entry in file_data:
            if entry['filename'] == selected_file and entry['soundcard_channel'] == soundcard_channel:
                pi_name = entry['pi']
                break
        else:
            return 'Selected song not found in the JSON file'
        if pi_name == 'pi2':
            pi = pi2
        elif pi_name == 'pi3':
            pi = pi3
            target_volume = 85
        with open(file_path, 'w') as file:
            json.dump(file_data, file)
        import re
        match = re.search(r'hw:(\d+)', soundcard_channel)
        if match:
            soundcard_number = match.group(1)
        else:
            return 'Invalid soundcard channel'
        # Calculate the step size for volume increase
        step_size = target_volume / (fade_duration / fade_interval)

        # Get the process ID of the mpg123 process
        command = f'pgrep -f "mpg123 -a {soundcard_channel} Music/{selected_file}"'
        stdin, stdout, stderr = pi.exec_command(command)
        process_id = stdout.read().decode().strip()

        if process_id:
            # Increase the volume gradually
            for volume in range(0, target_volume + 1, int(step_size)):
                # Set the same volume for both Front Left and Front Right channels
                command = f'amixer -c {soundcard_number} set PCM Playback Volume {volume}%'
                pi.exec_command(command)
                time.sleep(fade_interval)
            print(selected_file)
            command = f'pkill -CONT -f "mpg123 Music/{selected_file}"'
            pi.exec_command(command)

            return f'Music resumed on {pi}'
        else:
            return 'No music is currently playing'
    else:
        return 'No music is currently playing'

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
    
@app.route('/get_task_status', methods=['GET'])
def get_task_status():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                file_data = json.load(file)
            return jsonify(file_data)
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify([])
    else:
        return jsonify([])
    
@app.route('/solve_task/<task_name>', methods=['POST'])
def solve_task(task_name):
    global start_time, sequence, code1, code2, code3, code4, code5, codesCorrect, squeak_job, bird_job, should_hint_shed_play
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
    game_status = get_game_status()
    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)
        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'solved'
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)
        socketio.emit('task_update', room="all_clients")
        if task_name == "paw-maze":
            if squeak_job == False:
                scheduler.add_job(start_squeak, 'interval', seconds=30, id='squeakjob')
                squeak_job = True
            publish.single("audio_control/ret-top/play", "squeek.ogg", hostname=broker_ip)
        elif task_name == "woef-woef":
            if game_status == {'status': 'playing'}:
                if bird_job == True:
                    scheduler.remove_job('birdjob')
                    bird_job = False
                publish.single("audio_control/ret-top/play", "hok.ogg", hostname=broker_ip)
                call_control_maglock("doghouse-lock", "locked")
        elif task_name == "squeekuence":
            if game_status == {'status': 'playing'}:
                call_control_maglock("lab-hatch-lock", "locked")
                time.sleep(4)
                publish.single("audio_control/ret-middle/play", "Background.ogg", hostname=broker_ip)
                fade_music_in()
                publish.single("audio_control/ret-top/volume", "3 Ambience.ogg", hostname=broker_ip)
            if squeak_job == True:
                scheduler.remove_job('squeakjob')
                squeak_job = False
        elif task_name == "flowers":
            code1 = True
            codesCorrect += 1
            call_control_maglock("green-led-keypad", "locked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "bloemen.ogg", hostname=broker_ip)
            call_control_maglock("green-led-keypad", "locked")
            time.sleep(10)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in()
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in()
        elif task_name == "kite-count":
            code2 = True
            codesCorrect += 1
            call_control_maglock("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "vlieger.ogg", hostname=broker_ip)
            call_control_maglock("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in()
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in()
        elif task_name == "number-feel":
            code3 = True
            codesCorrect += 1
            call_control_maglock("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "plantenbak.ogg", hostname=broker_ip)
            call_control_maglock("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in()
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in()
        elif task_name == "fence-decrypt":
            code4 = True
            codesCorrect += 1
            call_control_maglock("green-led-keypad", "unlocked")
            publish.single("audio_control/ret-top/play", "correct-effect.ogg", hostname=broker_ip)
            time.sleep(1)
            fade_music_out("Ambience")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "hek.ogg", hostname=broker_ip)
            call_control_maglock("green-led-keypad", "locked")
            time.sleep(5)
            if codesCorrect == 3 or codesCorrect == 4:
                fade_music_in()
            elif codesCorrect == 2 or codesCorrect == 1:
                print(codesCorrect)
            elif code5 == False:
                fade_music_in()
        elif task_name == "sinus-game":
            print("nothing yet")
        elif task_name == "squid-game":
            if game_status == {'status': 'playing'}:
                call_control_maglock("top_left_light", "unlocked")
                call_control_maglock("top_right_light", "unlocked")
                call_control_maglock("bottom_left_light", "unlocked")
                call_control_maglock("bottom_right_light", "unlocked")
                publish.single("audio_control/ret-middle/play", "gelukt.ogg", hostname=broker_ip)
                time.sleep(3)
                call_control_maglock("sliding-door-lock", "locked")
                time.sleep(6)
                if should_balls_drop == True:
                    call_control_maglock("ball-drop-lock", "locked")
                publish.single("audio_control/ret-middle/stop", "Background.ogg", hostname=broker_ip)
                publish.single("audio_control/ret-middle/play", "Dogsout.ogg", hostname=broker_ip)
        elif task_name == "tree-lights":
            if bird_job == True:
                scheduler.remove_job('birdjob')
                bird_job = False
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/all/play", "correct-effect.ogg", hostname=broker_ip)
                time.sleep(1)
                code5 = True
                print("3")
                call_control_maglock("blue-led", "unlocked")
                fade_out_thread = threading.Thread(target=fade_music_out("Ambience"))
                fade_out_thread.start()
                time.sleep(1)
                call_control_maglock("blue-led", "locked")
                call_control_maglock("green-led", "locked")
                call_control_maglock("red-led", "locked")
                time.sleep(1)
                call_control_maglock("green-led", "unlocked")
                call_control_maglock("red-led", "unlocked")
                call_control_maglock("blue-led", "unlocked")
                time.sleep(1)
                call_control_maglock("green-led", "locked")
                call_control_maglock("red-led", "locked")
                call_control_maglock("blue-led", "locked")
                time.sleep(1)
                call_control_maglock("green-led", "unlocked")
                call_control_maglock("red-led", "unlocked")
                call_control_maglock("blue-led", "unlocked")
                time.sleep(1)
                call_control_maglock("green-led", "locked")
                call_control_maglock("red-led", "locked")
                call_control_maglock("blue-led", "locked")
                sequence = 0
                time.sleep(1)
                publish.single("audio_control/ret-top/play", "boom.ogg", hostname=broker_ip)
                time.sleep(7)
                if code1 and code2 and code3 and code4 and code5:
                    print("executed")
                    time.sleep(7)
                    publish.single("audio_control/ret-top/play", "schuur_open.ogg", hostname=broker_ip)
                    time.sleep(5)
                    fade_music_in()
                    call_control_maglock("shed-door-lock", "locked")
                    code1 = False
                    code2 = False
                    code3 = False
                    code4 = False
                    code5 = False
                else:
                    fade_in_thread = threading.Thread(target=fade_music_in)
                    fade_in_thread.start()
        if code1 and code2 and code3 and code4 and code5:
            print("executed")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "schuur_open.ogg", hostname=broker_ip)
            time.sleep(5)
            fade_music_in()
            call_control_maglock("shed-door-lock", "locked")
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
            fade_music_in()
        if codesCorrect == 1 and should_hint_shed_play == True:
            should_hint_shed_play = False
            print("TRIGGERED")
            time.sleep(2)
            publish.single("audio_control/ret-top/play", "after1code.ogg", hostname=broker_ip)
            time.sleep(4)
            fade_music_in()
        with app.app_context():
            return jsonify({'message': 'Task updated successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error updating task'})
@app.route('/skip_task/<task_name>', methods=['POST'])
def skip_task(task_name):
    global bird_job, code1, code2, code3, code4, code5, sequence, codesCorrect
    file_path = os.path.join(current_dir, 'json', 'tasks.json')

    try:
        with open(file_path, 'r+') as file:
            tasks = json.load(file)

        for task in tasks:
            if task['task'] == task_name:
                task['state'] = 'skipped'
        if task_name == "tree-lights":
            code5 = True
            call_control_maglock("blue-led", "locked")
            call_control_maglock("green-led", "locked")
            call_control_maglock("red-led", "locked")
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
            call_control_maglock("shed-door-lock", "locked")
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
@app.route('/pend_task/<task_name>', methods=['POST'])
def pend_task(task_name):
    file_path = os.path.join(current_dir, 'json', 'tasks.json')

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
@app.route('/reset_task_statuses', methods=['POST'])
def reset_task_statuses():
    global sequence
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
    sequence = 0
    update_game_status('awake')
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
def reset_prepare():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
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
@app.route('/reset_puzzles', methods=['POST'])
def reset_puzzles():
    global code1, code2, code3, code4, code5, sequence, codesCorrect, should_hint_shed_play
    update_game_status('awake')
    should_hint_shed_play = True
    codesCorrect = 0
    code1 = False
    code2 = False
    code3 = False
    code4 = False
    code5 = False
    with open('json/sensor_data.json', 'r') as file:
        devices = json.load(file)

    # Iterate over devices
    for device in devices:
        if device["type"] in ["maglock"]:
            if device["name"] == "gang-licht-1":
                call_control_maglock(device["name"], "unlocked")
            else:
                call_control_maglock(device["name"], "locked")
    return "puzzles reset"

# Function to read the retriever status from the JSON file
def read_game_status():
    with open('json/retrieverStatus.json', 'r') as file:
        data = json.load(file)
    return data.get('status', 'awake')  # Default status is 'awake'

# Function to update the retriever status in the JSON file
def update_game_status(status):
    data = {"status": status}
    with open('json/retrieverStatus.json', 'w') as file:
        json.dump(data, file)

@app.route('/get_game_status', methods=['GET'])
def get_game_status():
    game_status = read_game_status()
    return {"status": game_status}

@app.route('/wake_room', methods=['POST'])
def wake_room():
    # Update the retriever status to 'awake'
    try:
        with open('json/sensor_data.json', 'r') as file:
            devices = json.load(file)

        # Iterate over devices
        for device in devices:
            if device["type"] in ["light"] and device["name"] != "green-led" and device["name"] != "red-led" and device["name"] != "blue-led" and device["name"] != "red-led-keypad" and device["name"] != "green-led-keypad":
                call_control_maglock(device["name"], "unlocked")
        update_game_status('awake')
        return "room awakened"
    except Exception as e:
        update_game_status('awake')
        return jsonify({'success': False, 'error': str(e)})
@app.route('/control_light', methods=['POST'])
def control_light():
    print("hi")
    light_name = request.json.get('light_name')
    print(light_name)
    if light_name == "Light-1" and check_rule("light-1-garden"):
        call_control_maglock("light-1-garden", "locked")
    elif light_name == "Light-1":
        call_control_maglock("light-1-garden", "unlocked")
        print(light_name)
    elif light_name == "Light-2":
        call_control_maglock("light-2-garden", "locked" if check_rule("light-2-garden") else "unlocked")
    elif light_name == "Light-3":
        call_control_maglock("light-3-garden", "locked" if check_rule("light-3-garden") else "unlocked")
    elif light_name == "Light-4":
        call_control_maglock("light-4-garden", "locked" if check_rule("light-4-garden") else "unlocked")
    elif light_name == "Light-5":
        call_control_maglock("light-1-shed", "locked" if check_rule("light-1-shed") else "unlocked")
    elif light_name == "Light-6":
        call_control_maglock("light-1-alley", "locked" if check_rule("light-1-alley") else "unlocked")
    elif light_name == "Light-7":
        if check_rule("blacklight"):
            call_control_maglock("blacklight", "locked")
            call_control_maglock("portal-light", "locked")
        else:
            call_control_maglock("blacklight", "unlocked")
            call_control_maglock("portal-light", "unlocked")
    return jsonify({'message': f'Light {light_name} control command executed successfully'})
@app.route('/snooze_game', methods=['POST'])
def snooze_game():
    try:
        update_game_status('snoozed')

        # Load device information from sensor_data.json
        with open('json/sensor_data.json', 'r') as file:
            devices = json.load(file)

        # Iterate over devices
        for device in devices:
            if device["type"] in ["maglock", "light"]:
                call_control_maglock(device["name"], "locked")
        return "Room snoozed"
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/add_task', methods=['POST'])
def add_task():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
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
    
@app.route('/remove_task', methods=['POST'])
def remove_task():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
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
    
@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    file_path = os.path.join(current_dir, 'json', 'tasks.json')
    
    try:
        with open(file_path, 'r') as file:
            tasks = json.load(file)
        return jsonify(tasks)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])
    
@app.route('/play_music', methods=['POST'])
def play_music():
    data = request.json
    message = data.get('message')
    print(message)
    publish.single("audio_control/play", message, hostname=broker_ip)
    return jsonify({"status": "success"})
@app.route('/stop_music', methods=['POST'])
def stop_music():
    global squeak_job, bird_job
    if bird_job == True:
        scheduler.remove_job('birdjob')
        bird_job = False
    if squeak_job == True:
        scheduler.remove_job('squeakjob')
        squeak_job = False
    publish.single("audio_control/all/full_stop", "stop", hostname=broker_ip)
    # Wipe the entire JSON file by overwriting it with an empty list
    file_path = os.path.join(current_dir, 'json', 'file_status.json')
    with open(file_path, 'w') as file:
        json.dump([], file)
    return "Music stopped"
@app.route('/backup-top-pi', methods=['POST'])
def backup_top_pi():
    ssh.exec_command('./commit_and_push.sh')
    return "Top pi backed up"

@app.route('/backup-middle-pi', methods=['POST'])
def backup_middle_pi():
    ssh.exec_command('./commit_and_push.sh')
    return "Middle pi backed up"

def control_maglock():
    global squeak_job, should_balls_drop, player_type
    maglock = request.form.get('maglock')
    action = request.form.get('action')
    print(maglock)
    print(action)
    sensor_data = read_sensor_data2()
    for sensor in sensor_data:
        if sensor['name'] == maglock and (sensor['type'] == 'maglock' or sensor['type'] == 'light'):
            pi_name = sensor['pi']
            if "gang-licht-1" in maglock or "key-drop-lock" in maglock or "entrance-door-lock" in maglock:
                print(maglock)
                # Reverse the action for this specific case
                action = 'locked' if action == 'unlocked' else 'unlocked'
            # Publish the MQTT message with the appropriate Pi's name
            mqtt_message = f"{sensor['pin']} {action}"
            publish.single(f"actuator/control/{pi_name}", mqtt_message, hostname=broker_ip)
            return("done")
@app.route('/control_maglock', methods=['POST'])
def control_maglock_route():
    return control_maglock()


def call_control_maglock(maglock, action):
    global squeak_job, should_balls_drop, player_type
    print(maglock)
    print(action)
    sensor_data = read_sensor_data2()
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
            return("done")
API_URL = 'http://192.168.0.105:5001/current_state'

@app.route('/get_state', methods=['GET'])
def get_state():
    try:
        # Make a GET request to the API to fetch the current state
        response = requests.get(API_URL)
        if response.status_code == 200:
            state = response.json().get('state')
        else:
            state = 'unknown'
    except requests.exceptions.RequestException:
        state = 'unknown'
    return jsonify({'state': state})

API_URL_SENSORS = 'http://192.168.0.104:5000/sensor/status/'
def get_sensor_status(sensor_number):
    try:
        response = requests.get(API_URL_SENSORS + str(sensor_number))
        if response.status_code == 200:
            return response.json().get('status')
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        return 'unknown'
    
API_URL_SHED_KEYPAD = 'http://192.168.0.104:5000/keypad/pressed_keys'

def get_shed_keypad_code():
    try:
        response = requests.get(API_URL_SHED_KEYPAD)
        if response.status_code == 200:
            pressed_keys_arrays = response.json().get('pressed_keys_arrays')
            if pressed_keys_arrays:
                # Get the last-used code from the array
                last_used_code_array = pressed_keys_arrays[-1]
                last_used_code = ''.join(last_used_code_array)
                return last_used_code
            else:
                return 'No code entered yet'
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        return 'unknown'

API_URL_SENSORS_PI2 = 'http://192.168.0.105:5001/sensor/status/'

def get_sensor_status_pi2(sensor_number):
    try:
        response = requests.get(API_URL_SENSORS_PI2 + str(sensor_number))
        if response.status_code == 200:
            return response.json().get('status')
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        return 'unknown'
with open('json/sensor_data.json', 'r') as json_file:
    sensors = json.load(json_file)
def monitor_sensor_statuses():
    global sequence, should_hint_shed_play
    global code1, code2, code3, code4, code5
    global codesCorrect
    global last_keypad_code
    while True:
        #green_house_ir_status = get_ir_sensor_status(14)
        #red_house_ir_status = get_ir_sensor_status(20)
        #blue_house_ir_status = get_ir_sensor_status(18)
        #entrance_door_status = get_sensor_status(14)
        sinus_status = get_sinus_status()
        #top_left_kraken = get_sensor_status_pi2(15)
        #bottom_left_kraken = get_sensor_status_pi2(16)
        #top_right_kraken = get_sensor_status_pi2(20)
        #bottom_right_kraken = get_sensor_status_pi2(23)
        last_used_keypad_code = get_shed_keypad_code()
        if last_used_keypad_code != last_keypad_code:
            last_keypad_code = last_used_keypad_code  # Update the last keypad code
            if last_used_keypad_code == "1528" and code1 == False:
                code1 = True
                solve_task("flowers")
            elif (last_used_keypad_code == "7867" or last_used_keypad_code == "8978") and code2 == False:
                code2 = True
                solve_task("kite-count")
            elif last_used_keypad_code == "0128" and code3 == False:
                code3 = True
                solve_task("number-feel")
            elif last_used_keypad_code == "5038" and code4 == False:
                code4 = True
                solve_task("fence-decrypt")
            else:
                ssh.exec_command("raspi-gpio set 12 op dh")
                time.sleep(1)
                ssh.exec_command("raspi-gpio set 12 op dl")
        if sinus_status == "solved" and aborted == False:
            solve_task("sinus-game")
            #pi2.exec_command("mpg123 -a hw:1,0 Music/pentakill.mp3")
        time.sleep(0.1)
# Start a new thread for monitoring sensor statuses
@app.route('/reset-checklist', methods=['POST'])
def reset_checklist():
    try:
        # Read the current checklist data
        with open(CHECKLIST_FILE, 'r') as file:
            checklist_data = json.load(file)

        # Reset the completed status of all tasks
        for item in checklist_data:
            item['completed'] = False

        # Write the updated data back to the file
        with open(CHECKLIST_FILE, 'w') as file:
            json.dump(checklist_data, file, indent=2)
        socketio.emit('checklist_update', "message", room="all_clients")
    except Exception as e:
        print(f"Error resetting checklist: {str(e)}")
    return jsonify({'success': True, 'message': 'Checklist reset successfully'})
@app.route('/add_sensor', methods=['GET', 'POST'])
def add_sensor():
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

        # Add the new sensor to the list
        sensors.append(new_sensor)

        # Save the updated sensor data to the JSON file
        with open('json/sensor_data.json', 'w') as json_file:
            json.dump(sensors, json_file, indent=4)
        update_sensor_data_on_pis(pi)

        return redirect(url_for('list_sensors'))

    return render_template('add_sensor.html')

def update_sensor_data_on_pis(pi):
    success_message = "Sensor data updated successfully. Updated script sent to the following IP addresses:<br>"

    # Read Raspberry Pi data from JSON file
    with open('json/raspberry_pis.json') as json_file:
        raspberry_pis = json.load(json_file)

    for raspberry_pi in raspberry_pis:
        if raspberry_pi["hostname"] == pi:
            ip = raspberry_pi["ip_address"]
            try:
                # Create an SSH session for the Raspberry Pi
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))

                # Create an SFTP session over the existing SSH connection
                sftp = ssh.open_sftp()

                # Transfer the updated file to the Raspberry Pi
                sftp.put('json/sensor_data.json', '/home/pi/sensor_data.json')

                success_message += f"- {ip}<br>"

                # Close the SFTP session and SSH connection
                sftp.close()
                ssh.close()
            except Exception as e:
                return f'Error occurred while sending updated script to {ip}: {e}'

            break  # No need to continue searching for matching Raspberry Pi

    return success_message

@app.route('/remove_sensor', methods=['GET', 'POST'])
def remove_sensor():
    # Access the global sensors variable
    global sensors

    if request.method == 'POST':
        # Retrieve the selected sensor name to remove
        sensor_name_to_remove = request.form['sensor_name']

        # Read the existing sensor data from the JSON file
        with open('json/sensor_data.json', 'r') as json_file:
            sensors = json.load(json_file)

        # Remove the sensor from the list
        updated_sensors = [sensor for sensor in sensors if sensor['name'] != sensor_name_to_remove]

        # Save the updated sensor data back to the JSON file
        with open('json/sensor_data.json', 'w') as json_file:
            json.dump(updated_sensors, json_file, indent=4)

        # Update sensor data on the Raspberry Pi devices
        update_result = update_sensor_data_on_pis("ret")

        return f"{update_result}<br>Redirecting to sensor list...<meta http-equiv='refresh' content='2;url={url_for('list_sensors')}'>"

    return render_template('remove_sensor.html', sensors=sensors)
@app.route('/scare_button', methods=['POST'])
def scare_button():
    publish.single("audio_control/for-corridor/play", "Buzzer.ogg", hostname=broker_ip)
    publish.single("audio_control/for-corridor/volume", "100 Buzzer.ogg", hostname=broker_ip)
    return "Scared the players :)"
@app.route('/list_sensors')
def list_sensors():
    # Read the sensor data from the JSON file
    with open('json/sensor_data.json', 'r') as json_file:
        sensors = json.load(json_file)

    # Render the template with the updated sensor data
    return render_template('list_sensors.html', sensors=sensors)
def start_bird_sounds():
    publish.single("audio_control/ret-tree/play", "Gull.ogg", hostname=broker_ip)
    time.sleep(8)
    publish.single("audio_control/ret-tree/play", "Duck.ogg", hostname=broker_ip)
    time.sleep(8)
    publish.single("audio_control/ret-tree/play", "Eagle.ogg", hostname=broker_ip)
def start_squeak():
    publish.single("audio_control/ret-top/play", "squeek.ogg", hostname=broker_ip)

API_URL_IR_SENSORS = 'http://192.168.0.114:5001/ir-sensor/status/'

def get_ir_sensor_status(sensor_number):
    try:
        response = requests.get(API_URL_IR_SENSORS + str(sensor_number))
        if response.status_code == 200:
            return response.json().get('status')
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        return 'unknown'
sensor_thread = threading.Thread(target=monitor_sensor_statuses)
sensor_thread.daemon = True

API_URL_SINUS = 'http://192.168.0.105:5001/sinus-game/state'

def get_sinus_status():
    try:
        response = requests.get(API_URL_SINUS)
        if response.status_code == 200:
            return response.json().get('state')
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        return 'unknown'
#@app.route('/turn_on', methods=['POST'])
#def turn_on():
    maglock = request.form['maglock']
    return turn_on_maglock(maglock)

#@app.route('/turn_off', methods=['POST'])
#def turn_off():
    maglock = request.form['maglock']
    return turn_off_maglock(maglock)


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
timer_value = 3600  # Initial timer value in seconds
timer_thread = None  # Reference to the timer thread
speed = 1
timer_running = False  # Flag to indicate if the timer is running
def read_timer_value():
    try:
        with open(TIMER_FILE, 'r') as file:
            return float(file.read().strip())
    except FileNotFoundError:
        return timer_value  # Default timer value if the file doesn't exist

def write_timer_value(value):
    with open(TIMER_FILE, 'w') as file:
        file.write(str(value))

def update_timer():
    global timer_value, speed, timer_running
    while timer_value > 0 and timer_running:
        timer_value = max(timer_value - speed, 0)
        write_timer_value(timer_value)
        threading.Event().wait(1)
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
@app.route('/timer/start', methods=['POST'])
def start_timer():
    global timer_thread, timer_value, speed, timer_running, bird_job, start_time
    update_game_status('playing')
    if bird_job == False:
        scheduler.add_job(start_bird_sounds, 'interval', minutes=1, id='birdjob')
        bird_job = True
    start_time = datetime.now()
    if timer_thread is None or not timer_thread.is_alive():
        timer_value = 3600  # Reset timer value to 60 minutes
        write_timer_value(timer_value)
        timer_running = True
        timer_thread = threading.Thread(target=update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        fade_music_out("Lounge")
        time.sleep(1)
        publish.single("audio_control/ret-top/play", "Ambience.ogg", hostname=broker_ip)
        fade_music_in()
    return 'Timer started'

@app.route('/timer/stop', methods=['POST'])
def stop_timer():
    global timer_thread, timer_running, timer_value, kraken1, kraken2, kraken3, kraken4, bird_job, start_time
    update_game_status('awake')
    #pi2.exec_command("raspi-gpio set 4 op dl \n raspi-gpio set 7 op dl \n raspi-gpio set 8 op dl \n raspi-gpio set 1 op dl")
    reset_task_statuses()
    stop_music()
    end_time = datetime.now()
    if start_time is not None:
        write_game_data(start_time, end_time)
    start_time = None
    if timer_thread is not None and timer_thread.is_alive():
        write_timer_value(timer_value)
        timer_thread = threading.Thread(target=update_timer)
        timer_running = False
        timer_thread = None  # Stop the timer thread

    return 'Timer stopped'

@app.route('/timer/speed', methods=['POST'])
def update_timer_speed():
    global speed
    change = float(request.form['change'])  # Get the change in timer speed from the request
    speed += change
    return 'Timer speed updated'

@app.route('/timer/reset-speed', methods=['POST'])
def reset_timer_speed():
    global speed
    speed = 1
    return 'Timer speed reset'

@app.route('/timer/value', methods=['GET'])
def get_timer_value():
    return str(read_timer_value())

@app.route('/timer/get-speed', methods=['GET'])
def get_timer_speed():
    global speed
    return str(speed)

@app.route('/timer/pause', methods=['POST'])
def pause_timer():
    global timer_thread, timer_running

    if timer_thread is not None and timer_thread.is_alive() and timer_running:
        timer_running = False
        return 'Timer paused'
    else:
        return 'Timer is not running or already paused'

@app.route('/timer/continue', methods=['POST'])
def continue_timer():
    global timer_thread, timer_running
    current_game_state = get_game_status()
    if current_game_state == {'status': 'prepared'}:
        update_game_status('playing')
    if timer_thread is not None and not timer_thread.is_alive() and not timer_running:
        timer_running = True
        timer_thread = threading.Thread(target=update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        return 'Timer continued'
    else:
        return 'Timer is already running or not paused'
@app.route('/timer/pause-state', methods=['GET'])
def get_pause_state():
    global timer_running
    return jsonify(timer_running)
update_game_status('awake')
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
@app.route('/prepare', methods=['POST'])
def prepare_game():
    global client, pi_service_statuses, player_type, preparedValue, should_hint_shed_play
    should_hint_shed_play = True
    prefix = request.form.get('prefix')
    print(prefix)
    if get_game_status() == {'status': 'prepared'}:
        return jsonify({"message": preparedValue}), 200
    reset_prepare()
    # Assuming you have logic for preparing the game
    # Load Raspberry Pi configuration from JSON file
    with open('json/raspberry_pis.json', 'r') as file:
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
    update_game_status("prepared")
    time.sleep(0.1)
    publish.single("audio_control/ret-top/play", "Lounge.ogg", hostname=broker_ip)
    return jsonify({"message": converted_statuses}), 200
if romy == False:
    turn_on_api()
    start_scripts()

@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_interrupt)
    socketio.run(app, host='0.0.0.0', port=80, allow_unsafe_werkzeug=True)