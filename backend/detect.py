import cv2
from ultralytics import YOLO
import os
from datetime import datetime
import traceback

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Resolve model path relative to this file so imports work regardless of cwd
model_path = os.path.join(os.path.dirname(__file__), "best.pt")

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model weights not found at {model_path}")

# Load trained pothole model
try:
    model = YOLO(model_path)
    model.to("cpu")
    print(f"✅ Model loaded from {model_path}")
except Exception as e:
    print(f"❌ Failed to load model from {model_path}: {e}")
    raise


def _save_debug_image(img, folder, prefix):
    os.makedirs(folder, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = os.path.join(folder, f"{prefix}_{ts}.jpg")
    try:
        cv2.imwrite(path, img)
        print(f"Saved debug image: {path}")
    except Exception as e:
        print(f"Failed to save debug image {path}: {e}")
    return path


def _extract_box_info(box):
    try:
        xyxy = box.xyxy[0]
        if hasattr(xyxy, 'cpu'):
            xyxy = xyxy.cpu().numpy()
        x1, y1, x2, y2 = map(int, xyxy)
    except Exception:
        x1, y1, x2, y2 = map(int, box.xyxy[0])

    try:
        score = float(box.conf[0].cpu().numpy()) if hasattr(box.conf[0], 'cpu') else float(box.conf[0])
    except Exception:
        score = float(box.conf[0])

    try:
        cls = int(box.cls[0].cpu().numpy()) if hasattr(box.cls[0], 'cpu') else int(box.cls[0])
    except Exception:
        cls = int(box.cls[0])

    return x1, y1, x2, y2, score, cls


def detect_pothole(input_path=None, conf=0.15, save_output=False, output_folder="uploads"):
    debug = {
        'uploaded_path': input_path,
        'file_exists': False,
        'file_size_bytes': None,
        'image_loaded': False,
        'image_shape': None,
        'video_props': None,
        'model_path': model_path,
        'model_loaded': True,
        'predictions': [],
        'conf_threshold': conf,
        'saved': {},
    }

    try:
        if not input_path:
            return {"status": "error", "message": "No input provided", 'debug': debug}

        debug['file_exists'] = os.path.exists(input_path)
        if not debug['file_exists']:
            return {"status": "error", "message": f"File not found: {input_path}", 'debug': debug}

        debug['file_size_bytes'] = os.path.getsize(input_path)
        ext = os.path.splitext(input_path)[1].lower()
        os.makedirs(output_folder, exist_ok=True)

        if ext in ALLOWED_IMAGE_EXTENSIONS:
            img = cv2.imread(input_path)
            debug['image_loaded'] = img is not None
            if img is None:
                return {"status": "error", "message": "Image load failed or file is corrupted", 'debug': debug}

            debug['image_shape'] = img.shape
            debug['file_type'] = 'image'

            original_path = _save_debug_image(img, output_folder, 'debug_original')
            debug['saved']['original'] = original_path

            print(f"Running model on image: {input_path} (conf={conf})")
            results = model(img, conf=conf, verbose=False)

            vis = img.copy()
            detections = 0
            preds = []

            for r in results:
                boxes = getattr(r, 'boxes', None)
                if boxes is None:
                    continue
                for box in boxes:
                    x1, y1, x2, y2, score, cls = _extract_box_info(box)
                    label = model.names.get(cls, str(cls))
                    preds.append({'bbox': [x1, y1, x2, y2], 'score': score, 'class': cls, 'label': label})
                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(vis, f"{label} {score:.2f}", (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    detections += 1

            output_path = os.path.join(output_folder, f"output_pothole_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.jpg")
            cv2.imwrite(output_path, vis)
            debug['saved']['prediction_vis'] = output_path
            debug['predictions'] = preds
            debug['detection_count'] = detections

            return {
                "status": "ok",
                "type": "image",
                "detections": detections,
                "predictions": preds,
                "output_image": output_path,
                "debug": debug,
            }

        if ext in ALLOWED_VIDEO_EXTENSIONS:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                return {"status": "error", "message": "Unable to open video file", 'debug': debug}

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            debug['video_props'] = {'fps': fps, 'width': width, 'height': height, 'frame_count': frame_count}
            debug['file_type'] = 'video'

            output_path = None
            writer = None
            if save_output:
                output_path = os.path.join(output_folder, f"output_pothole_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(output_path, fourcc, fps or 25, (width, height))

            total_detections = 0
            detected_frames = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame is None:
                    continue

                frame_small = cv2.resize(frame, (640, 360))
                results = model(frame_small, conf=conf, verbose=False)
                frame_detected = False

                for r in results:
                    boxes = getattr(r, 'boxes', None)
                    if boxes is None:
                        continue
                    for box in boxes:
                        x1, y1, x2, y2, score, cls = _extract_box_info(box)
                        label = model.names.get(cls, str(cls))
                        sx = frame.shape[1] / 640
                        sy = frame.shape[0] / 360
                        x1, y1, x2, y2 = int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f"{label} {score:.2f}", (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        total_detections += 1
                        frame_detected = True

                if frame_detected:
                    detected_frames += 1
                if save_output and writer:
                    writer.write(frame)

            cap.release()
            if writer:
                writer.release()

            debug['detection_count'] = total_detections
            debug['detected_frames'] = detected_frames
            if output_path:
                debug['saved']['prediction_vis'] = output_path

            return {
                "status": "ok",
                "type": "video",
                "frames": frame_count,
                "detected_frames": detected_frames,
                "detections": total_detections,
                "output_video": output_path,
                "debug": debug,
            }

        return {"status": "error", "message": f"Unsupported file extension: {ext}", 'debug': debug}

    except Exception as e:
        tb = traceback.format_exc()
        print("Detection exception:\n", tb)
        return {"status": "error", "message": "Detection failed", "details": str(e), "traceback": tb, 'debug': debug}


def detect_road(video_path, conf=0.25, save_output=True):
    print("Using model:", getattr(model, 'model', None))
    print("Confidence:", conf)
    print("Video path:", video_path)
    results = model(video_path, conf=conf, save=save_output)
    detections = 0
    for r in results:
        if r.boxes is not None:
            detections += len(r.boxes)
    print("Detections count:", detections)
    return {
        "status": "ok",
        "detections": detections
    }
