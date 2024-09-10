import cv2
import pygame
import sys
import mediapipe as mp
import numpy as np
import random
import paho.mqtt.client as mqtt
# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((640, 480))
pygame.display.set_caption("Escape Room Puzzle")

# Colors for the squares
colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)]  # Green, Blue, Red, Yellow
target_positions = [(100, 100), (200, 100), (300, 100), (400, 100)]
square_positions = [(random.randint(50, 590), random.randint(50, 430)) for _ in range(4)]
square_selected = [False, False, False, False]  # Track if a square is selected
grab_threshold = 50  # Distance threshold for grabbing a square
pinch_threshold = 0.05  # Distance threshold between thumb and index finger tips for pinch detection
currently_grabbed_square = None  # Track which square is currently being grabbed

# Initialize MediaPipe Hands module
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Initialize MediaPipe Drawing module for drawing landmarks
mp_drawing = mp.solutions.drawing_utils

# Open a video capture object (0 for the default camera)
cap = cv2.VideoCapture(0)

def draw_background(frame):
    # Convert the frame to RGB (Pygame uses RGB, OpenCV uses BGR)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Convert the frame to a Pygame surface
    frame = np.rot90(frame)  # Rotate if needed
    frame = pygame.surfarray.make_surface(frame)
    screen.blit(frame, (0, 0))

def is_near(p1, p2, threshold):
    """Check if point p1 is near point p2 within a given threshold."""
    return abs(p1[0] - p2[0]) < threshold and abs(p1[1] - p2[1]) < threshold

def is_pinching(hand_landmarks):
    """Check if the index finger and thumb tips are close together (indicating a pinch)."""
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    
    distance = np.linalg.norm([index_finger_tip.x - thumb_tip.x, index_finger_tip.y - thumb_tip.y])
    return distance < pinch_threshold

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Draw the webcam feed as the background
    draw_background(frame)
    
    # Flip the frame horizontally so movement isn't mirrored
    frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    
    # Process the frame to detect hands
    results = hands.process(frame_rgb)
    
    # Get the index fingertip position for hand interaction
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Extract the index fingertip coordinates
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_finger_pos = (int(index_finger_tip.x * screen.get_width()), int(index_finger_tip.y * screen.get_height()))
            
            # Detect pinch
            if is_pinching(hand_landmarks):
                if currently_grabbed_square is None:  # Check if no square is currently being grabbed
                    # Check if the index finger is near any square and "grab" it
                    for i, pos in enumerate(square_positions):
                        if is_near(index_finger_pos, pos, grab_threshold):  # Check if the finger is close enough to "grab" the square
                            currently_grabbed_square = i  # Mark this square as being grabbed
                            square_positions[i] = index_finger_pos
                            break  # Only grab one square
                else:
                    # Move the currently grabbed square
                    square_positions[currently_grabbed_square] = index_finger_pos
            else:
                # Release the square if pinch is released
                currently_grabbed_square = None
            
            # Draw landmarks on the frame (optional for visualization)
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
    
    # Draw the target positions with outlines
    for pos, color in zip(target_positions, colors):
        pygame.draw.rect(screen, color, (*pos, 50, 50), 2)  # The '2' here specifies the thickness of the outline
    
    # Draw the colored squares on top of the webcam feed
    for pos, color in zip(square_positions, colors):
        pygame.draw.rect(screen, color, (*pos, 50, 50))
    
    # Check if the squares are in the correct positions
    if all(abs(square_positions[i][0] - target_positions[i][0]) < 20 and 
           abs(square_positions[i][1] - target_positions[i][1]) < 20 for i in range(4)):
        font = pygame.font.Font(None, 74)
        text = font.render("Lekker sicko", True, (255, 255, 255))
        screen.blit(text, (100, 200))
    
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

cap.release()
pygame.quit()

