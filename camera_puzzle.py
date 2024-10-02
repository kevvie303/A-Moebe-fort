import cv2
import pygame
import sys
import mediapipe as mp
import numpy as np
import random
import paho.mqtt.client as mqtt

# MQTT configuration
mqtt_broker = "192.168.0.103"
hostname = "mlv-herbalist"  # Replace with your actual hostname
topic_solved = f"state_data/{hostname}/webcam"
topic_unsolved = f"webcam_control/{hostname}"

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(topic_unsolved)

def on_message(client, userdata, msg):
    if msg.payload.decode() == "unsolved":
        scramble_images()

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker)
mqtt_client.loop_start()

# Function to scramble images
def scramble_images():
    global square_positions
    square_positions = [(random.randint(50, screen_width - 250), random.randint(50, screen_height - 250)) for _ in range(4)]
    for i in range(len(locked_squares)):
        locked_squares[i] = False  # Reset the locked state

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.set_caption("Escape Room Puzzle")

# Load images and outlines
image_paths = ['image1.png', 'image2.png', 'image3.png', 'image4.png']
outline_paths = ['outline1.png', 'outline2.png', 'outline3.png', 'outline4.png']
images = [pygame.image.load(img_path) for img_path in image_paths]
outlines = [pygame.image.load(out_path) for out_path in outline_paths]

# Resize images and outlines to 200x200
# images = [pygame.transform.scale(img, (200, 200)) for img in images]
# outlines = [pygame.transform.scale(outline, (200, 200)) for outline in outlines]

# Set target positions (outline positions)
target_positions = [(200, 100), (550, 100), (900, 100), (1250, 100)]
square_positions = [(random.randint(50, screen_width - 250), random.randint(50, screen_height - 250)) for _ in range(4)]
grab_threshold = 100  # Increased threshold to make grabbing easier
pinch_threshold = 0.05
snap_threshold = 50
currently_grabbed_square = None
locked_squares = [False, False, False, False]
grab_offset = (0, 0)

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Open the video capture object
cap = cv2.VideoCapture(0)

def draw_background(frame):
    frame = cv2.resize(frame, (screen_width, screen_height))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    frame = pygame.surfarray.make_surface(frame)
    screen.blit(frame, (0, 0))

def is_near(p1, p2, threshold):
    return abs(p1[0] - p2[0]) < threshold and abs(p1[1] - p2[1]) < threshold

def is_pinching(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    distance = np.linalg.norm([index_finger_tip.x - thumb_tip.x, index_finger_tip.y - thumb_tip.y])
    return distance < pinch_threshold

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    draw_background(frame)
    frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_finger_pos = (int(index_finger_tip.x * screen_width), int(index_finger_tip.y * screen_height))
            
            if is_pinching(hand_landmarks):
                if currently_grabbed_square is None:
                    for i, pos in enumerate(square_positions):
                        img_center = (pos[0] + 100, pos[1] + 100)
                        if is_near(index_finger_pos, img_center, grab_threshold) and not locked_squares[i]:
                            currently_grabbed_square = i
                            grab_offset = (index_finger_pos[0] - pos[0], index_finger_pos[1] - pos[1])
                            break
                else:
                    if not locked_squares[currently_grabbed_square]:
                        square_positions[currently_grabbed_square] = (index_finger_pos[0] - grab_offset[0], index_finger_pos[1] - grab_offset[1])
            else:
                currently_grabbed_square = None

            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Draw the outlines first
    for pos, outline in zip(target_positions, outlines):
        screen.blit(outline, pos)

    # Then draw the draggable images on top of the outlines
    for i, (pos, img) in enumerate(zip(square_positions, images)):
        screen.blit(img, pos)
        
        # Snap into place when close to the target and make sure it's drawn in front
        if is_near(pos, target_positions[i], snap_threshold) and not locked_squares[i]:
            square_positions[i] = target_positions[i]
            locked_squares[i] = True

    # Check if all squares are snapped into place
    if all(locked_squares):
        mqtt_client.publish(topic_solved, "solved")
        font = pygame.font.Font(None, 74)
        text = font.render("Lekker sicko", True, (255, 255, 255))
        screen.blit(text, (screen_width // 2 - 200, screen_height // 2))

    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            mqtt_client.loop_stop()  # Stop MQTT loop
            mqtt_client.disconnect()  # Disconnect from MQTT broker
            pygame.quit()
            sys.exit()

cap.release()
pygame.quit()
