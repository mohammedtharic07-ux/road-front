import cv2
import os
from datetime import datetime

# Non-GUI camera test for server environments - save one frame from first available camera
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        print(f"Camera index {i} OPENED ✅")
        ret, frame = cap.read()
        if ret and frame is not None:
            out_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            out_path = os.path.join(out_dir, f"camera_{i}_{ts}.jpg")
            cv2.imwrite(out_path, frame)
            print(f"Saved camera frame to {out_path}")
        else:
            print(f"Failed to capture frame from camera {i}")
        cap.release()
        break
    else:
        print(f"Camera index {i} not working ❌")
