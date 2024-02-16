from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import json
import paramiko
import atexit
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
load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app)
#command = 'python relay_control.py'
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
        # CHANGE TO ["ping", "-c", "1", "-W", "1", ip] on UNIX
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



def monitor_ssh_connections():
    while True:
        establish_ssh_connection()
        # Check the connections every 60 seconds
        time.sleep(60)

# Start the monitoring thread
monitor_thread = threading.Thread(target=monitor_ssh_connections)
monitor_thread.daemon = True  # Make the thread a daemon to exit when the main program exits
broker_ip = "192.168.50.253"  # IP address of the broker Raspberry Pi
#broker_ip = "192.168.1.216"
# Define the topic prefix to subscribe to (e.g., "sensor_state/")
prefix_to_subscribe = "state_data/"
sensor_states = {}
# Callback function to process incoming MQTT messages

def on_message(client, userdata, message):
    # Extract the topic and message payload
    global code1, code2, code3, code4, code5, bird_job, squeak_job, kraken1, kraken2, kraken3, kraken4, should_balls_drop
    topic = message.topic
    parts = topic.split("/")
    sensor_name = parts[-1]  # Extract the last part of the topic (sensor name)
    sensor_state = message.payload.decode("utf-8")
    sensor_states[sensor_name] = sensor_state

    print(f"Received MQTT message - Sensor: {sensor_name}, State: {sensor_state}")

    if sensor_name in sensor_states:
        sensor_states[sensor_name] = sensor_state
        update_json_file()
        print("State changed. Updated JSON.")
    print(sensor_states)
    if check_rule("maze-sensor"):
        if check_task_state("paw-maze") == "pending":
            print("solved")
    if check_rule("entrance_door"):
        current_game_state = get_game_status()
        if current_game_state == {'status': 'prepared'}:
            start_timer()
    global sequence
    if check_rule("green_house_ir") and sequence == 0:
        task_state = check_task_state("tree-lights")
        if task_state == "pending":
            pi3.exec_command("raspi-gpio set 15 op dh")
            print("1")
            sequence = 1
    if check_rule("red_house_ir") and sequence == 1:
        task_state = check_task_state("tree-lights")
        if task_state == "pending":
            pi3.exec_command("raspi-gpio set 21 op dh")
            print("2")
            sequence = 2
    elif check_rule("red_house_ir") and sequence <= 0:
        task_state = check_task_state("tree-lights")
        if task_state == "pending":
            pi3.exec_command("raspi-gpio set 21 op dh")
            time.sleep(0.5)
            pi3.exec_command("raspi-gpio set 21 op dl")
            pi3.exec_command("raspi-gpio set 15 op dl")
            sequence = 0
    if check_rule("blue_house_ir") and sequence == 2:
        task_state = check_task_state("tree-lights")
        if task_state == "pending":
            solve_task("tree-lights")
    elif check_rule("blue_house_ir") and sequence != 2:
        task_state = check_task_state("tree-lights")
        if task_state == "pending":
            pi3.exec_command("raspi-gpio set 23 op dh")
            time.sleep(0.5)
            pi3.exec_command("raspi-gpio set 23 op dl")
            pi3.exec_command("raspi-gpio set 21 op dl")
            pi3.exec_command("raspi-gpio set 15 op dl")
            sequence = 0
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

        if is_checked:
            execute_lock_command(task)
        else:
            execute_unlock_command(task)

        # Update the checklist status
        update_checklist(task, is_checked)
        socketio.emit('checklist_update', {'task': task, 'isChecked': is_checked}, room="all_clients")
        print(f"Locking action executed successfully for task: {task}, isChecked: {is_checked}")
        return jsonify({'success': True, 'message': 'Locking action executed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def execute_lock_command(task):
    try:
        # Add logic to map tasks to corresponding SSH commands for locking
        if task == "Doe de entree deur dicht":
            print("locked")
            #command = "raspi-gpio set 25 op dl"
            #stdin, stdout, stderr = pi3.exec_command(command)
            # You can handle the command execution results if needed
        # Add more mappings as needed
    except Exception as e:
        print(f"Error executing lock command: {str(e)}")

def execute_unlock_command(task):
    try:
        # Add logic to map tasks to corresponding SSH commands for unlocking
        if task == "Doe de entree deur dicht":
            print("unlocked")
            #command = "raspi-gpio set 25 op u"
            #stdin, stdout, stderr = pi3.exec_command(command)
            # You can handle the command execution results if needed
        # Add more mappings as needed
    except Exception as e:
        print(f"Error executing unlock command: {str(e)}")

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
            elif item_type == "button" and item["state"] == "Locked":
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
if loadMqtt == True:
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
@app.route('/krijgsgevangenis')
def pow():
    return render_template('pow.html')
def start_scripts():
    sensor_thread.start()
    monitor_thread.start()
    update_game_status('awake')
    #pi2.exec_command('python mqtt.py')
    time.sleep(0.5)
    #pi2.exec_command('nohup python status.py > /dev/null 2>&1 &')    
    time.sleep(0.5)
    pi2.exec_command('python actuator.py')
    #pi3.exec_command('python mqtt.py')
    time.sleep(0.5)
    pi2.exec_command('python mqtt.py')
    #pi3.exec_command('nohup python status.py > /dev/null 2>&1 &')
    time.sleep(0.5)
    ssh.exec_command('python mqtt.py')
    #scheduler.add_job(monitor_sensor_statuses, 'interval', seconds=0.1)

@app.route('/add_music1', methods=['POST'])
def add_music1():
    file = request.files['file']
    if file:
        try:
            # Get the file extension
            filename, file_extension = os.path.splitext(file.filename)
            
            # Check if the file extension is allowed
            allowed_extensions = ['.mp3', '.wav', '.ogg']
            if file_extension.lower() in allowed_extensions:
                # Create an SFTP client to transfer the file
                sftp = pi2.open_sftp()
                
                # Modify the file path to be relative to the Flask application
                local_path = os.path.join(app.root_path, 'uploads', file.filename)
                
                # Save the file to the modified local path
                file.save(local_path)
                
                # Save the file to the Music folder on the Pi
                remote_path = '/home/pi/Music/' + filename + file_extension
                sftp.put(local_path, remote_path)
                
                # Close the SFTP client
                sftp.close()
                
                # Delete the local file after transferring
                os.remove(local_path)

                sftp = pi3.open_sftp()
                
                # Modify the file path to be relative to the Flask application
                local_path = os.path.join(app.root_path, 'uploads', file.filename)
                
                # Save the file to the modified local path
                file.save(local_path)
                
                # Save the file to the Music folder on the Pi
                remote_path = '/home/pi/Music/' + filename + file_extension
                sftp.put(local_path, remote_path)
                
                # Close the SFTP client
                sftp.close()
                
                # Delete the local file after transferring
                os.remove(local_path)
                
                return 'Music added successfully!'
            else:
                return 'Invalid file type. Only .mp3, .wav, and .ogg files are allowed.'
        except IOError as e:
            return f'Error: {str(e)}'
        finally:
            # Close the SSH connection
            print("h")
    else:
        return 'No file selected.'


@app.route('/media_control')
def media_control():
    try:
        # Create an SFTP client to list files in the Music folder
        sftp = pi2.open_sftp()
        
        # List all MP3 files in the Music folder
        remote_path = '/home/pi/Music'
        mp3_files = [file for file in sftp.listdir(remote_path) if file.endswith('.mp3')]
        
        return render_template('media_control.html', mp3_files=mp3_files)
    except IOError as e:
        return f'Error: {str(e)}'
    finally:
        # Close the SFTP client and SSH connection
        sftp.close()
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


@app.route('/file_selection')
def file_selection():
    stdin, stdout, stderr = pi2.exec_command('ls ~/Music')
    music_files = stdout.read().decode().splitlines()
    return render_template('file_selection.html', music_files=music_files)


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
@app.route('/fade_music_out', methods=['POST'])
def fade_music_out():
        # Gradually reduce the volume from 80 to 40
    for volume in range(25, 10, -1):
        # Send the volume command to the Raspberry Pi
        command = f'echo "volume {volume}" | sudo tee /tmp/mpg123_fifo'
        
        if check_task_state("squeekuence") == "solved":
            stdin, stdout, stderr = pi2.exec_command(command)
        else:
            stdin, stdout, stderr = pi3.exec_command(command)
        
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
    time.sleep(1)
    pi3.exec_command('mpg123 -a hw:0,0 Music/prehint.mp3')
    return "Volume faded successfully"
def fade_music_out2():

        # Gradually reduce the volume from 80 to 40
    for volume in range(65, 1, -1):
        # Send the volume command to the Raspberry Pi
        command = f'echo "volume {volume}" | sudo tee /tmp/mpg123_fifo'
        stdin, stdout, stderr = pi3.exec_command(command)
        stdin, stdout, stderr = pi2.exec_command(command)
        # Wait for a short duration between volume changes
        time.sleep(0.05)  # Adjust the sleep duration as needed
def fade_music_out3():
        # Gradually reduce the volume from 80 to 40
    for volume in range(25, 0, -1):
        # Send the volume command to the Raspberry Pi
        command = f'echo "volume {volume}" | sudo tee /tmp/mpg123_fifo'
        stdin, stdout, stderr = pi2.exec_command(command)
        # Wait for a short duration between volume changes
        time.sleep(0.2)  # Adjust the sleep duration as needed
@app.route('/fade_music_in', methods=['POST'])
def fade_music_in():
        # Gradually reduce the volume from 80 to 40
    for volume in range(10, 25, 1):
        # Send the volume command to the Raspberry Pi
        command = f'echo "volume {volume}" | sudo tee /tmp/mpg123_fifo'
        if check_task_state("squeekuence") == "solved":
            stdin, stdout, stderr = pi2.exec_command(command)
        else:
            stdin, stdout, stderr = pi3.exec_command(command)
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
        if task_name == "Stroomstoring":
            if game_status == {'status': 'playing'}:
                cause_shortcircuit()
        elif task_name == "woef-woef":
            if game_status == {'status': 'playing'}:
                if bird_job == True:
                    scheduler.remove_job('birdjob')
                    bird_job = False
                pi3.exec_command("mpg123 -a hw:0,0 Music/hok.mp3 \n raspi-gpio set 4 op dh")
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
        if task_name == "Wastafel-sleutel":
            print("skipped!")
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
            pi3.exec_command('mpg123 -a hw:0,0 Music/schuur_open.mp3')
            pi3.exec_command('raspi-gpio set 16 op dh')
            code1 = False
            code2 = False
            code3 = False
            code4 = False
            code5 = False
        with open(file_path, 'w') as file:
            json.dump(tasks, file, indent=4)

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
@app.route('/reset_puzzles', methods=['POST'])
def reset_puzzles():
    global aborted
    global code1
    global code2
    global code3
    global code4
    global code5
    global codesCorrect
    codesCorrect == 0
    aborted = True
    code1 = False
    code2 = False
    code3 = False
    code4 = False
    code5 = False
    update_game_status('awake')
    pi3.exec_command('raspi-gpio set 16 op dl')
    pi2.exec_command('sudo pkill -f sinus_game.py')
    pi2.exec_command('pkill -f sensor_board.py')
    pi2.exec_command('pkill -9 mpg123')
    pi2.exec_command('raspi-gpio set 12 op dl')
    pi2.exec_command('raspi-gpio set 1 op dl')
    pi2.exec_command('raspi-gpio set 7 op dl')
    pi2.exec_command('raspi-gpio set 8 op dl')
    time.sleep(3)
    #pi2.exec_command('sudo python sinus_game.py')
    #pi2.exec_command('python sensor_board.py')
    time.sleep(15)
    aborted = False
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
    pi3.exec_command('raspi-gpio set 12 op dl \n raspi-gpio set 7 op dl \n raspi-gpio set 1 op dl \n raspi-gpio set 8 op dl')
    ssh.exec_command('raspi-gpio set 15 op dl \n raspi-gpio set 25 op dl')
    update_game_status('awake')
    return "room awakened"
@app.route('/control_light', methods=['POST'])
def control_light():
    print("hi")
    light_name = request.json.get('light_name')
    print(light_name)
    if light_name == "Light-1" and check_rule("light-1-garden"):
        command = "raspi-gpio set 1 op dh"
    elif light_name == "Light-1":
        command = "raspi-gpio set 1 op dl"
        print(light_name)
    if light_name == "Light-2" and check_rule("light-2-garden"):
        command = "raspi-gpio set 7 op dh"
    elif light_name == "Light-2":
        command = "raspi-gpio set 7 op dl"
        print(light_name)
    if light_name == "Light-3" and check_rule("light-3-garden"):
        command = "raspi-gpio set 12 op dh"
        print(light_name)
    elif light_name == "Light-3":
        command = "raspi-gpio set 12 op dl"
    if light_name == "Light-4" and check_rule("light-4-garden"):
        command = "raspi-gpio set 8 op dh"
        print(light_name)
    elif light_name == "Light-4":
        command = "raspi-gpio set 8 op dl"
    if light_name == "Light-5" and check_rule("light-1-shed"):
        command = "raspi-gpio set 15 op dh"
        print(light_name)
    elif light_name == "Light-5":
        command = "raspi-gpio set 15 op dl"
    if light_name == "Light-6" and check_rule("light-1-alley"):
        command = "raspi-gpio set 25 op dh"
        print(light_name)
    elif light_name == "Light-6":
        command = "raspi-gpio set 25 op dl"
    if light_name == "Light-7" and check_rule("blacklight"):
        command = "raspi-gpio set 17 op dh \n raspi-gpio set 10 op dh"
        print(light_name)
    elif light_name == "Light-7":
        command = "raspi-gpio set 17 op dl \n raspi-gpio set 10 op dl"
    if light_name == "Light-8":
        command = "raspi-gpio set 4 op dh"
    if light_name == "Light-8":
        pi2.exec_command(command)
    elif light_name == "Light-5" or light_name == "Light-6" or light_name == "Light-7":
        ssh.exec_command(command)
    else:
        pi3.exec_command(command)
    return jsonify({'message': f'Light {light_name} control command executed successfully'})
@app.route('/snooze_game', methods=['POST'])
def snooze_game():
    light1off = 'raspi-gpio set 12 op dh'
    light2off = 'raspi-gpio set 7 op dh'
    light3off = 'raspi-gpio set 1 op dh'
    light4off = 'raspi-gpio set 8 op dh'
    lightsoff = f"{light1off}; {light2off}; {light3off}; {light4off}"
    pi3.exec_command(lightsoff)
    ssh.exec_command('raspi-gpio set 17 op dh \n raspi-gpio set 10 op dh')
    ssh.exec_command('raspi-gpio set 27 op dh')
    ssh.exec_command('raspi-gpio set 15 op dh \n raspi-gpio set 25 op dh \n raspi-gpio set 6 op dh \n raspi-gpio set 16 op dh \n raspi-gpio set 20 op dh \n raspi-gpio set 21 op dh')
    pi3.exec_command('raspi-gpio set 16 op dh')
    pi3.exec_command('raspi-gpio set 25 op dh')
    update_game_status('snoozed')
    return "room snoozed"
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
def set_starting_volume(soundcard_channel):
    command = f'amixer -c {soundcard_channel} set PCM Playback Volume 25%'
    pi2.exec_command(command)
    return "Volume set to 25%"
@app.route('/stop_music', methods=['POST'])
def stop_music():
    # Stop the music on pi2
    stdin, stdout, stderr = pi2.exec_command('pkill -9 mpg123 \n echo "stop" | sudo tee /tmp/mpg123_fifo')
    stdin, stdout, stderr = pi3.exec_command('pkill -9 mpg123 \n echo "stop" | sudo tee /tmp/mpg123_fifo')
    # Wipe the entire JSON file by overwriting it with an empty list
    file_path = os.path.join(current_dir, 'json', 'file_status.json')
    with open(file_path, 'w') as file:
        json.dump([], file)

    return 'Music stopped on pi2/pi3 and JSON wiped.'

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
    sensor_data = read_sensor_data2()
    for sensor in sensor_data:
        if sensor['name'] == maglock and (sensor['type'] == 'maglock' or sensor['type'] == 'light'):
            pi_name = sensor['pi']
            if "gang-licht-1" in maglock:
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
@app.route('/add_sensor', methods=['GET', 'POST'])
def add_sensor():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        item_type = request.form['type']
        pin = int(request.form['pin'])
        pi = request.form['pi']

        # Create a new sensor dictionary with an initial state of "Not triggered"
        new_sensor = {
            "name": name,
            "type": item_type,
            "pin": pin,
            "pi": pi,
            "state": "initial"
        }

        # Add the new sensor to the list
        sensors.append(new_sensor)

        # Save the updated sensor data to the JSON file
        with open('json/sensor_data.json', 'w') as json_file:
            json.dump(sensors, json_file, indent=4)
        ssh_sessions = [ssh, pi2, pi3]

        success_message = "Script sent successfully to the following IP addresses:<br>"

        for session in ssh_sessions:
            if session:
                try:
                    # Create an SFTP session over the existing SSH connection
                    sftp = session.open_sftp()
                    print(sftp)
                    # Transfer the file to the Raspberry Pi
                    sftp.put('json/sensor_data.json', '/home/pi/sensor_data.json')

                    success_message += f"- {session.get_transport().getpeername()[0]}<br>"

                    # Close the SFTP session
                    sftp.close()
                except Exception as e:
                    return f'Error occurred while sending script: {e}'

        return redirect(url_for('list_sensors'))

    return render_template('add_sensor.html')
@app.route('/list_sensors')
def list_sensors():
    return render_template('list_sensors.html', sensors=sensors)
def start_bird_sounds():
    pi3.exec_command("mpg123 -a hw:1,0 Music/Gull.mp3")
    time.sleep(8)
    pi3.exec_command("mpg123 -a hw:1,0 Music/Duck.mp3")
    time.sleep(8)
    pi3.exec_command("mpg123 -a hw:1,0 Music/Eagle.mp3")
def start_squeak():
    pi3.exec_command("mpg123 -a hw:0,0 Music/squeek.mp3")

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

@app.route('/timer/start', methods=['POST'])
def start_timer():
    global timer_thread, timer_value, speed, timer_running, bird_job
    if bird_job == False:
        scheduler.add_job(start_bird_sounds, 'interval', minutes=1, id='birdjob')
        bird_job = True
    update_game_status('playing')
    if timer_thread is None or not timer_thread.is_alive():
        timer_value = 3600  # Reset timer value to 60 minutes
        write_timer_value(timer_value)
        timer_running = True
        timer_thread = threading.Thread(target=update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        fade_music_out2()
    time.sleep(0.5)
    load_command = f'echo "load /home/pi/Music/Ambience.mp3" | sudo tee /tmp/mpg123_fifo'
    pi3.exec_command(load_command)
    time.sleep(0.5)
    fade_music_in()
    return 'Timer started'

@app.route('/timer/stop', methods=['POST'])
def stop_timer():
    global timer_thread, timer_running, timer_value, kraken1, kraken2, kraken3, kraken4, bird_job
    update_game_status('awake')
    pi2.exec_command("raspi-gpio set 4 op dl \n raspi-gpio set 7 op dl \n raspi-gpio set 8 op dl \n raspi-gpio set 1 op dl")
    kraken1 = False
    kraken2 = False
    kraken3 = False
    kraken4 = False
    if bird_job == True:
        scheduler.remove_job('birdjob')
        bird_job = False
    reset_task_statuses()
    stop_music()
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
def check_scripts_running(ssh, script_name):
    try:
        stdin, stdout, stderr = ssh.exec_command(f'pgrep -af "python {script_name}"')
        process_count = len(stdout.read().decode().split('\n')) - 1
        return process_count > 0
    except Exception as e:
        return False

def check_service_status(ip_address, service_name):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
    stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service_name}')
    status = stdout.read().decode().strip() == 'active'
    ssh.close()
    return status

# Define a function to get Raspberry Pis by prefix
def get_raspberry_pis_with_prefix(prefix, scanner):
    pi_devices = scanner.scan_for_raspberrypi()  # Adjust the range as necessary
    return [(ip, hostname) for ip, _, hostname in pi_devices if hostname and hostname.startswith(prefix)]

@app.route('/prepare', methods=['POST'])
def prepare_game():
    prefix = request.form.get('prefix')
    scanner = NetworkScanner()
    raspberry_pis = get_raspberry_pis_with_prefix(prefix, scanner)

    results = {}
    for ip, hostname in raspberry_pis:
        mqtt_status = check_service_status(ip, 'mqtt.service')
        sound_status = check_service_status(ip, 'sound.service')
        print(sound_status)
        print(mqtt_status)
        results[hostname] = {"mqtt.service": mqtt_status, "sound.service": sound_status}
        #should be tested thoroughly

    return jsonify({"message": results}), 200

if romy == False:
    turn_on_api()
    start_scripts()

@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_interrupt)
    socketio.run(app, host='0.0.0.0', port=80)