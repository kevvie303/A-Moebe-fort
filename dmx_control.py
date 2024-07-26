import paho.mqtt.publish as publish
import json

# MQTT Settings
MQTT_BROKER = '192.168.1.27'
MQTT_PORT = 1883
MQTT_TOPIC = 'actuator/control/dmx/raspberrypi'  # Replace 'your_hostname' with the actual hostname

def send_dmx_command(pan, tilt, colour, gobo):
    """Send DMX command via MQTT."""
    # Create a JSON payload
    payload = {
        'pan': pan,
        'tilt': tilt,
        'colour': colour,
        'gobo': gobo
    }
    # Convert payload to JSON string
    payload_str = json.dumps(payload)

    # Publish the message
    publish.single(MQTT_TOPIC, payload=payload_str, qos=0, hostname=MQTT_BROKER, port=MQTT_PORT)
    print(f"Published to {MQTT_TOPIC}: {payload_str}")

# Example usage
send_dmx_command(pan=128, tilt=64, colour=12, gobo=0)
