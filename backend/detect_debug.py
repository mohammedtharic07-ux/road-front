import cv2
from ultralytics import YOLO
import os
from datetime import datetime
import traceback

# Resolve model path relative to this file
model_path = os.path.join(os.path.dirname(__file__), "best.pt")

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model weights not found at {model_path}")

# Load model
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


def detect_pothole(input_path=None, conf=0.15, save_output=False, output_folder="uploads"):
    debug = {
        'uploaded_path': input_path,
        'image_loaded': False,
        'image_shape': None,
        'model_path': model_path,
        'model_loaded': True,
        'predictions': None,
        'conf_threshold': conf,
        'saved': {}
    }

    try:
        if not input_path:
            return {"status": "error", "message": "No input provided", 'debug': debug}

        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}", 'debug': debug}

        ext = os.path.splitext(input_path)[1].lower()

        if ext in [".jpg", ".jpeg", ".png", ".webp", ".jfif"]:
            img = cv2.imread(input_path)
            debug['image_loaded'] = img is not None
            if img is None:
                debug['image_shape'] = None
                return {"status": "error", "message": "cv2.imread returned None (image failed to load)", 'debug': debug}

            debug['image_shape'] = img.shape

            orig_path = _save_debug_image(img, output_folder, 'debug_original')
            debug['saved']['original'] = orig_path

            # Use the BGR image read by OpenCV directly; Ultralytics accepts OpenCV-style arrays.
            pre_img = cv2.resize(img, (640, 640))
            pre_path = _save_debug_image(pre_img, output_folder, 'debug_preprocessed')
            debug['saved']['preprocessed'] = pre_path

            print(f"Running model on image: {input_path} (conf={conf})")
            results = model(pre_img, conf=conf, verbose=False)

            preds = []
            detections = 0
            vis = img.copy()

            for r in results:
                boxes = getattr(r, 'boxes', None)
                if boxes is None:
                    continue
                for box in boxes:
                    try:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        score = float(box.conf[0].cpu().numpy()) if hasattr(box.conf[0], 'cpu') else float(box.conf[0])
                        cls = int(box.cls[0].cpu().numpy()) if hasattr(box.cls[0], 'cpu') else int(box.cls[0])
                        label = model.names.get(cls, str(cls))
                    except Exception:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        score = float(box.conf[0])
                        cls = int(box.cls[0])
                        label = model.names.get(cls, str(cls))

                    preds.append({
                        'bbox':[x1, y1, x2, y2],
                        'score': score,
                        'class': cls,
                        'label': label
                    })

                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(vis, f"{label} {score:.2f}", (x1, max(20, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    detections += 1

            debug['predictions'] = preds

            if save_output:
                out_img_path = os.path.join(output_folder, f"output_pothole_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.jpg")
                try:
                    cv2.imwrite(out_img_path, vis)
                    debug['saved']['prediction_vis'] = out_img_path
                    print(f"Saved detection visualization: {out_img_path}")
                except Exception as e:
                    print(f"Failed to save detection visualization: {e}")

            return {
                "status": "ok",
                "type": "image",
                "detections": detections,
                "predictions": preds,
                "output_image": debug['saved'].get('prediction_vis'),
                "debug": debug
            }

        # Video handling (simpler path)
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return {"status": "error", "message": "Video open failed", 'debug': debug}

        total_detections = 0
        frame_count = 0
        detected_frames = 0

        os.makedirs(output_folder, exist_ok=True)
        out_path = None
        writer = None
        if save_output:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            out_path = os.path.join(output_folder, f"output_pothole_{timestamp}.mp4")
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
            print(f"📹 Video properties - FPS: {fps}, Resolution: {w}x{h}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            frame_detected = False

            small = cv2.resize(frame, (640, 360))
            results = model(small, conf=conf, verbose=False)

            for r in results:
                boxes = getattr(r, 'boxes', None)
                if boxes is None:
                    continue
                for box in boxes:
                    total_detections += 1
                    frame_detected = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    sx = frame.shape[1] / 640
                    sy = frame.shape[0] / 360
                    x1, y1, x2, y2 = int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)

                    score = float(box.conf[0])
                    cls = int(box.cls[0])
                    label = model.names.get(cls, str(cls))

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"{label} {score:.2f}", (x1, max(20, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if frame_detected:
                detected_frames += 1
                print(f"✅ Frame {frame_count}: Found detection(s) in video")

            if save_output and writer:
                writer.write(frame)

            if frame_count >= 500:
                print(f"🛑 Reached frame limit (500 frames processed)")
                break

        cap.release()
        if writer:
            writer.release()

        print(f"📊 Video detection summary:")
        print(f"   Total frames: {frame_count}")
        print(f"   Frames with detections: {detected_frames}")
        print(f"   Total detections: {total_detections}")

        return {
            "status": "ok",
            "type": "video",
            "frames": frame_count,
            "detected_frames": detected_frames,
            "detections": total_detections,
            "output_video": out_path if save_output else None,
            'debug': debug
        }

    except Exception as e:
        tb = traceback.format_exc()
        print("Detection exception:\n", tb)
        return {"status": "error", "message": str(e), 'traceback': tb, 'debug': debug}
