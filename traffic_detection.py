import cv2
import torch
from picamera2 import Picamera2, NullPreview
import numpy as np
import time
import os
import warnings
import RPi.GPIO as GPIO

# Suppress warnings and environment variables
warnings.filterwarnings("ignore", category=FutureWarning)
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_FONTDIR", None)
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

# Initialize camera
picam2 = Picamera2()
try:
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"}))
    picam2.start_preview(NullPreview())
except Exception as e:
    print(f"Error configuring camera: {e}")
    exit()

# Video writer setup
width, height = 640, 480
fps = 30
output_path = '/home/user/Desktop/recess_project/output_video.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# Load YOLOv5 model
try:
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='/home/user/yolov5/runs/train/exp/weights/best.pt', force_reload=True)
    model.conf = 0.3
    model.iou = 0.45
except Exception as e:
    print(f"Error loading YOLOv5: {e}")
    exit()

# GPIO setup for LEDs
GPIO.setmode(GPIO.BCM)
# Lane A LEDs
GPIO.setup(17, GPIO.OUT)  # Red A
GPIO.setup(27, GPIO.OUT)  # Yellow A
GPIO.setup(22, GPIO.OUT)  # Green A
# Lane B LEDs
GPIO.setup(23, GPIO.OUT)  # Red B
GPIO.setup(24, GPIO.OUT)  # Yellow B
GPIO.setup(25, GPIO.OUT)  # Green B

# Function to control traffic lights
def set_traffic_lights(lane_a_state, lane_b_state, duration):
    """Set LEDs for Lane A and Lane B based on state (R, Y, G) and wait for duration."""
    # Turn off all LEDs
    GPIO.output([17, 27, 22, 23, 24, 25], GPIO.LOW)
    # Lane A
    if lane_a_state == 'R':
        GPIO.output(17, GPIO.HIGH)  # Red A ON
    elif lane_a_state == 'Y':
        GPIO.output(27, GPIO.HIGH)  # Yellow A ON
    elif lane_a_state == 'G':
        GPIO.output(22, GPIO.HIGH)  # Green A ON
    # Lane B
    if lane_b_state == 'R':
        GPIO.output(23, GPIO.HIGH)  # Red B ON
    elif lane_b_state == 'Y':
        GPIO.output(24, GPIO.HIGH)  # Yellow B ON
    elif lane_b_state == 'G':
        GPIO.output(25, GPIO.HIGH)  # Green B ON
    time.sleep(duration)

# Traffic light timing logic
def control_traffic_lights(lane_a_cars, lane_b_cars):
    """Adjust green light duration based on car counts."""
    base_green_time = 10  # Base green light duration (seconds)
    yellow_time = 3       # Yellow light duration
    min_green_time = 5    # Minimum green time
    max_green_time = 20   # Maximum alley_time

    # Calculate green light durations based on car's count
    total_cars = lane_a_cars + lane_b_cars
    if total_cars == 0:
        green_a_time = green_b_time = base_green_time
    else:
        # Proportionally allocate green time based on car counts
        green_a_time = min_green_time + (lane_a_cars / total_cars) * (max_green_time - min_green_time)
        green_b_time = min_green_time + (lane_b_cars / total_cars) * (max_green_time - min_green_time)

    # Traffic light cycle
    print(f"Lane A: {lane_a_cars} cars, Green for {green_a_time:.1f}s | Lane B: {lane_b_cars} cars, Green for {green_b_time:.1f}s")
    # Lane A green, Lane B red
    set_traffic_lights('G', 'R', green_a_time)
    # Lane A yellow, Lane B red
    set_traffic_lights('Y', 'R', yellow_time)
    # Lane A red, Lane B green
    set_traffic_lights('R', 'G', green_b_time)
    # Lane A red, Lane B yellow
    set_traffic_lights('R', 'Y', yellow_time)

try:
    picam2.start()
    print("Camera started, recording... Press Ctrl+C to stop.")
    frame_count = 0
    while True:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame_count += 1
        if frame_count % 3 != 0:
            out.write(frame_bgr)
            continue

        # Process frame with YOLOv5
        results = model(frame_bgr)
        detections = results.pred[0]

        # Count cars in each lane (split frame at x = width/2)
        lane_a_cars = 0  # Left lane (x < width/2)
        lane_b_cars = 0  # Right lane (x >= width/2)
        for pred in detections:
            if pred[-1] == 0:  # Assuming class 0 is 'car'
                x_center = (pred[0] + pred[2]) / 2  # Center x-coordinate of bounding box
                if x_center < width / 2:
                    lane_a_cars += 1
                else:
                    lane_b_cars += 1

        print(f"Lane A cars: {lane_a_cars}, Lane B cars: {lane_b_cars}")

        # Control traffic lights based on car counts
        control_traffic_lights(lane_a_cars, lane_b_cars)

        # Annotate and save frame
        annotated_frame = frame_bgr.copy()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated_frame, f"Lane A: {lane_a_cars} | Lane B: {lane_b_cars} | {timestamp}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        out.write(annotated_frame)

except KeyboardInterrupt:
    print("Keyboard interrupt received, stopping...")
finally:
    picam2.stop()
    out.release()
    GPIO.cleanup()  # Clean up GPIO pins
    print("Recording stopped, video saved to", output_path)
	

