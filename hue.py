import requests
import time
import random

# Hue Bridge IP address and username
bridge_ip = '192.168.0.110'
username = 'hX2wWkAbCb30i0lLlIoDD2s5Fa6I0Nboa74sjCtj'

# URL to control the light state
def get_url(light_id):
    return f'http://{bridge_ip}/api/{username}/lights/{light_id}/state'

# Function to send a PUT request
def send_put_request(light_id, data):
    url = get_url(light_id)
    response = requests.put(url, json=data)
    return response.json()

# Function to turn the light on or off
def set_light_state(light_id, on):
    data = {"on": on}
    response = send_put_request(light_id, data)
    print(f'Set Light {light_id} {"On" if on else "Off"}: {response}')

# Function to make the light flicker like a fire
def flicker_light(light_id, duration, steps):
    for _ in range(steps):
        brightness = random.randint(50, 150)  # Brightness range for flickering
        hue = random.randint(4500, 5500)  # Hue range for warm yellow to orange
        sat = random.randint(200, 254)  # Saturation range for vibrant colors
        data = {"bri": brightness, "hue": hue, "sat": sat}
        response = send_put_request(light_id, data)
        print(f'Set State of Light {light_id}: {response}')
        time.sleep(0.1)

# Define the lamp layout and relationships
# This is a 2x4 grid with one lamp missing
# Using a 1-based index for light IDs as an example
lamp_layout = {
    1: [1, 2, 5],
    2: [1, 2, 3, 6],
    3: [2, 3, 4, 7],
    4: [3, 4, 8],
    5: [1, 5, 6],
    6: [2, 5, 6, 7],
    7: [3, 6, 7, 8],
    8: [4, 7, 8]
}

# Function to toggle a lamp on or off
def toggle_lamp(light_id):
    # Get current state
    current_state = requests.get(get_url(light_id)).json()
    if 'state' in current_state and 'on' in current_state['state']:
        current_on = current_state['state']['on']
        new_state = not current_on
        set_light_state(light_id, new_state)
        print(f'Toggled Light {light_id} to {"On" if new_state else "Off"}')

# Function to handle button press
def handle_button_press(light_id):
    if light_id in lamp_layout:
        for lamp in lamp_layout[light_id]:
            toggle_lamp(lamp)
    else:
        print(f'Light {light_id} is not in the layout')

# Example button press, SHOULD BE HANDLED BY MQTT. Make this script for specific pi's!
button_press_light_id = 2
handle_button_press(button_press_light_id)
