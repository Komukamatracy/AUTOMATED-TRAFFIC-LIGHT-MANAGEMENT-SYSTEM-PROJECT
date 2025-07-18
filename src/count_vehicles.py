import cv2
import torch
from picamera2 import Picamera2
import numpy as np
import time
import os
import warnings

# Suppress PyTorch FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Fix OpenCV/Qt compatibility for Bookworm
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_FONTDIR", None)
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

# Initialize Picamera2 with NullPreview
picam2 = Picamera2()
try:
    video_config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(video_config)
except Exception as e:
    print(f"Error configuring camera: {e}")
    exit()

# Video properties
width, height = 640, 480
fps = 30

# Initialize video writer
output_path = '/home/user/Desktop/recess_project/output_video.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# Load YOLOv5 model (nano for performance)
try:
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='/home/user/Desktop/recess_project/yolov5/runs/train/exp/weights/best.pt', force_reload=True)
    model.conf = 0.3  # Confidence threshold
    model.iou = 0.45  # IoU threshold to reduce NMS time
except Exception as e:
    print(f"Error loading YOLOv5: {e}")
    exit()

# Start camera
picam2.start()
print("Camera started, recording...")

record_duration = 30
start_time = time.time()
frame_count = 0

try:
    while True:
        # Capture frame
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Skip every other frame for performance
        frame_count += 1
        if frame_count % 3 != 0:  # Increased skipping for performance
            out.write(frame_bgr)  # Write unprocessed frame
            continue

        # Detect vehicles and people
        results = model(frame_bgr)
        detections = results.pred[0]
        #vehicle_count = sum(1 for pred in detections if pred[-1] in [2, 3, 5, 7])  # Vehicles: car, motorcycle, bus, truck
        toy_car_count = sum(1 for pred in detections if pred[-1] == 0)  # toycars
        #total_count = vehicle_count + person_count
        print(f"Toy cars detected: {toy_car_count}")

        # Use original frame (writable) for annotations
        annotated_frame = frame_bgr.copy()

        # Add total count and timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated_frame, f"Toy Cars: {toy_car_count} | {timestamp}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Write frame to output video
        out.write(annotated_frame)

        # Stop recording
        if time.time() - start_time > record_duration:
            break

finally:
    picam2.stop()
    out.release()
    print("Recording stopped, video saved to", output_path)
