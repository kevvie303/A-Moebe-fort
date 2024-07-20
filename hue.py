import requests
import time
import random

# Hue Bridge IP address and username
bridge_ip = '192.168.0.110'
username = 'hX2wWkAbCb30i0lLlIoDD2s5Fa6I0Nboa74sjCtj'
light_id = '2'  # Replace with your actual light ID

# URL to control the light state
url = f'http://{bridge_ip}/api/{username}/lights/{light_id}/state'

# Function to send a PUT request
def send_put_request(data):
    response = requests.put(url, json=data)
    return response.json()

# Turn the light on
data_on = {"on": True}
response_on = send_put_request(data_on)
print(f'Turn On: {response_on}')

# Function to make the light flicker like a fire
def flicker_light(duration, steps):
    for _ in range(steps):
        # Generate random brightness, hue, and saturation values to simulate flickering
        brightness = random.randint(50, 150)  # Brightness range for flickering
        hue = random.randint(4500, 5500)  # Hue range for warm yellow to orange
        sat = random.randint(200, 254)  # Saturation range for vibrant colors

        # Set light state
        data = {"bri": brightness, "hue": hue, "sat": sat}
        response = send_put_request(data)
        print(f'Set State: {response}')
        
        # Wait for a short period before the next change
        time.sleep(0.1)

# Flicker the light for 10 seconds with 100 steps
flicker_light(10, 100)

# Optionally, turn the light off again
data_off = {"on": False}
response_off = send_put_request(data_off)
print(f'Turn Off: {response_off}')
