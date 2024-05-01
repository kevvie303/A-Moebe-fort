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
current_dir = os.path.abspath(os.path.dirname(__file__))
def check_task_state(task_name):
    json_file_path = 'json/tasks.json'  # Set the path to your JSON file
    with open(json_file_path, 'r') as json_file:
        task_data = json.load(json_file)

    for task in task_data:
        if task["task"] == task_name:
            return task["state"]
    return "Task not found"
def get_game_status():
    game_status = read_game_status()
    return {"status": game_status}
def read_game_status():
    with open('json/retrieverStatus.json', 'r') as file:
        data = json.load(file)
    return data.get('status', 'awake')  # Default status is 'awake'
def solve_task(task_name):
    global start_time
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
                publish.single("audio_control/for-guard/play", "static.mp3", hostname="192.168.50.253")
                publish.single("audio_control/for-guard/volume", "100 static.mp3", hostname="192.168.50.253")
                publish.single("audio_control/for-corridor/play", "bgCorridor.ogg", hostname="192.168.50.253")
                time.sleep(5)
                publish.single("audio_control/for-guard/stop", "static.mp3", hostname="192.168.50.253")
                publish.single(f"actuator/control/guard_room_pi", "26 locked", hostname=broker_ip)
                publish.single("audio_control/for-guard/play", "drawerCorrect.ogg", hostname=broker_ip)
                time.sleep(2)
                publish.single(f"actuator/control/guard_room_pi", "20 unlocked", hostname=broker_ip)
        elif task_name == "granaat-allemaal":
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/all/play", "Sona.ogg", hostname=broker_ip)
                publish.single("audio_control/all/volume", "100 Sona.ogg", hostname=broker_ip)
                publish.single("audio_control/all/volume", "5 alarm.ogg", hostname=broker_ip)
        elif task_name == "3-objecten":
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/for-cell/volume", "40 newBg.ogg", hostname=broker_ip)
                publish.single(f"actuator/control/guard_room_pi", "21 locked", hostname=broker_ip)
                publish.single("audio_control/for-guard/play", "secretDoor.ogg", hostname=broker_ip)
                publish.single("audio_control/for-cell/play", "secretDoor.ogg", hostname=broker_ip)
                time.sleep(3)
                publish.single("audio_control/for-guard/play", "bgGuard.ogg", hostname=broker_ip)
                publish.single("audio_control/for-garderobe/play", "bgGuard.ogg", hostname=broker_ip)
                publish.single("audio_control/for-guard/volume", "100 bgGuard.ogg", hostname=broker_ip)
                publish.single("audio_control/for-garderobe/volume", "100 bgGuard.ogg", hostname=broker_ip)
        elif task_name == "scan-mendez":
            if game_status == {'status': 'playing'}:
                publish.single(f"actuator/control/corridor_pi", "21 unlocked", hostname=broker_ip)
                publish.single(f"actuator/control/corridor_pi", "12 locked", hostname=broker_ip)
                publish.single("audio_control/for-corridor/play", "Buzzer.ogg", hostname="192.168.50.253")
                publish.single("audio_control/for-corridor/volume", "100 Buzzer.ogg", hostname="192.168.50.253")
                publish.single(f"actuator/control/guard_room_pi", "20 locked", hostname=broker_ip)
                time.sleep(3)
                publish.single(f"actuator/control/corridor_pi", "21 locked", hostname=broker_ip)
        elif task_name == "scan-rosenthal":
            if game_status == {'status': 'playing'}:
                publish.single(f"actuator/control/corridor_pi", "13 unlocked", hostname=broker_ip)
                publish.single(f"actuator/control/corridor_pi", "20 locked", hostname=broker_ip)
                publish.single("audio_control/for-corridor/play", "Buzzer.ogg", hostname="192.168.50.253")
                publish.single("audio_control/for-corridor/volume", "100 Buzzer.ogg", hostname="192.168.50.253")
                publish.single("audio_control/for-poepdoos/play", "bgCorridor.ogg", hostname="192.168.50.253")
                time.sleep(3)
                publish.single(f"actuator/control/corridor_pi", "13 locked", hostname=broker_ip)
                publish.single("audio_control/for-poepdoos/play", "WC.ogg", hostname="192.168.50.253")
                publish.single("audio_control/for-poepdoos/volume", "100 WC.ogg", hostname="192.168.50.253")
        elif task_name == "kapstok-allemaal":
            if game_status == {'status': 'playing'}:
                publish.single("audio_control/for-garderobe/play", "jassenCorrect.ogg", hostname="192.168.50.253")
                time.sleep(1)
                publish.single(f"actuator/control/for-garderobe", "23 unlocked", hostname=broker_ip)
        elif task_name == "alarm-knop":
            if game_status == {'status': 'playing'}:
                publish.single(f"actuator/control/corridor_pi", "19 unlocked", hostname=broker_ip)
                publish.single(f"actuator/control/corridor_pi", "26 unlocked", hostname=broker_ip)
                publish.single(f"actuator/control/corridor_pi", "4 unlocked", hostname=broker_ip)
                publish.single(f"actuator/control/corridor_pi", "27 unlocked", hostname=broker_ip)
                publish.single("audio_control/for-poepdoos/stop", "WC.ogg", hostname=broker_ip)
                publish.single("audio_control/all/play", "alarm.ogg", hostname="192.168.50.253")
                publish.single("audio_control/all/volume", "100 alarm.ogg", hostname="192.168.50.253")
                #time.sleep(120)
                fade_music_out("alarm")
        return jsonify({'message': 'Task updated successfully'})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'message': 'Error updating task'})
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
def fade_music_out(file):
    global broker_ip
    print(file)
    if file == "alarm":
        time.sleep(120)
        initial_volume = 100
        final_volume = 40
    else:
        initial_volume = 35
        final_volume = 17

    # Gradually increase the volume
    current_volume = initial_volume
    while current_volume > final_volume:
        current_volume -= 1  # Increase volume by 1 each second
        payload = f"{int(current_volume)} {file}.ogg"
        if file == "alarm":
            publish.single("audio_control/all/volume", payload, hostname=broker_ip)
        else:
            publish.single("audio_control/raspberrypi/volume", payload, hostname=broker_ip)
        print(current_volume)
        if file == "alarm":
            time.sleep(0.05)
        else:
            time.sleep(0.25)
    return "Volume faded successfully"
def update_json_file():
    try:
        # Read existing JSON data
        with open("json/sensor_data.json", 'r') as json_file:
            sensor_data = json.load(json_file)
        print("Successfully loaded sensor_data.json")

        # Update sensor states in the JSON data
        for sensor in sensor_data:
            sensor_name = sensor["name"]
            if sensor_name in sensor_states:
                sensor["state"] = sensor_states[sensor_name]

        # Write the updated JSON data back to the file
        with open("json/sensor_data.json", 'w') as json_file:
            json.dump(sensor_data, json_file, indent=4)
        print("Successfully updated sensor_data.json")

    except Exception as e:
        print(f"Error updating JSON file: {e}")

broker_ip = "192.168.50.253"  # IP address of the broker Raspberry Pi
# Define the topic prefix to subscribe to (e.g., "sensor_state/")
prefix_to_subscribe = "state_data/"
sensor_states = {}
# Callback function to process incoming MQTT messages

pi_service_statuses = {}  # New dictionary to store service statuses for each Pi

# Function to handle incoming MQTT messages
def on_message(client, userdata, message):
    global sensor_states, pi_service_statuses
    
    # Extract the topic and message payload
    sensor_states = {}
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

    # Add print statements for debugging
    print(f"Sensor States: {sensor_states}")  # Print sensor_states for debugging
    #print(sensor_states)
    if get_game_status() == {'status': 'playing'}:
        if sensor_name == "rfid_corridor":
            print(sensor_state)
            mendez1 = 584185540695
            mendez2 = 584199238531
            roosenthaal1 = 584198160159
            roosenthaal2 = 584183068095
            sensor_state_int = int(sensor_state)
            print(roosenthaal2)
            if sensor_state_int == mendez1 or sensor_state_int == mendez2:
                if check_task_state("scan-mendez") == "pending":
                    solve_task("scan-mendez")
                print("Correct code")
            elif sensor_state_int == roosenthaal1 or sensor_state_int == roosenthaal2:
                if check_task_state("scan-rosenthal") == "pending":
                    solve_task("scan-rosenthal")
                print("Correct code")
        if check_rule("jas-1"):
            if check_task_state("kapstok-zuidafrika") == "pending":
                solve_task("kapstok-zuidafrika")
        if check_rule("jas-1") == False:
            if check_task_state("kapstok-zuidafrika") == "solved":
                pend_task("kapstok-zuidafrika")
        if check_rule("jas-2"):
            if check_task_state("kapstok-italie") == "pending":
                solve_task("kapstok-italie")
        if check_rule("jas-2") == False:
            if check_task_state("kapstok-italie") == "solved":
                pend_task("kapstok-italie")
        if check_rule("jas-3"):
            if check_task_state("kapstok-ijsland") == "pending":
                solve_task("kapstok-ijsland")
        if check_rule("jas-3") == False:
            if check_task_state("kapstok-ijsland") == "solved":
                pend_task("kapstok-ijsland")
        if check_rule("jas-1") and check_rule("jas-2") and check_rule("jas-3"):
            if check_task_state("kapstok-allemaal") == "pending":
                solve_task("kapstok-allemaal")
        if check_rule("grenade-1"):
            if check_task_state("granaat-tomsk") == "pending":
                solve_task("granaat-tomsk")
        if check_rule("grenade-1") == False:
            if check_task_state("granaat-tomsk") == "solved":
                pend_task("granaat-tomsk")
        if check_rule("grenade-2"):
            if check_task_state("granaat-khabarovsk") == "pending":
                solve_task("granaat-khabarovsk")
        if check_rule("grenade-2") == False:
            if check_task_state("granaat-khabarovsk") == "solved":
                pend_task("granaat-khabarovsk")
        if check_rule("grenade-3"):
            if check_task_state("granaat-soratov") == "pending":
                solve_task("granaat-soratov")
        if check_rule("grenade-3") == False:
            if check_task_state("granaat-soratov") == "solved":
                pend_task("granaat-soratov")
        if check_rule("grenade-1") and check_rule("grenade-2") and check_rule("grenade-3"):
            if check_task_state("granaat-allemaal") == "pending":
                solve_task("granaat-allemaal")
        if check_rule("camera_button"):
            if check_task_state("Stroomstoring") == "pending":
                solve_task("Stroomstoring")
        if check_rule("ehbo-kist") == False:
            if check_task_state("Medicijnkastje-open") == "pending":
                solve_task("Medicijnkastje-open")
        if check_rule("nightstand") == False:
            if check_task_state("Poster") == "pending":
                solve_task("Poster")
        if check_rule("3-objects"):
            if check_task_state("3-objecten") == "pending":
                solve_task("3-objecten")
        if check_rule("alarm-button"):
            if check_task_state("alarm-knop") == "pending":
                solve_task("alarm-knop")

client = mqtt.Client()

    # Set the callback function for incoming MQTT messages
client.on_message = on_message

    # Connect to the MQTT broker
client.connect(broker_ip, 1883)

    # Subscribe to all topics under the specified prefix
client.subscribe(prefix_to_subscribe + "#")  # Subscribe to all topics under the prefix
# Function to execute the delete-locks.py script
client.loop_forever()