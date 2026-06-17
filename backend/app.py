from flask import Flask, jsonify, request, session
from flask_cors import CORS
from db import mongo
from routes import routes
import os
import random
import logging
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from detect import detect_pothole

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# ---------------- INIT ---------------- #
# Serve frontend static files from the project `frontend` folder so frontend
# and backend share the same origin (helps with session cookies during dev).
frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app = Flask(__name__, static_folder=frontend_folder, static_url_path='')

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ---------------- #
app.secret_key = "supersecretkey123"

# CORS configuration for cross-origin requests (port 8000 frontend to port 5000 backend)
CORS(app, 
     resources={r"/*": {
         "origins": ["http://127.0.0.1:8000", "http://127.0.0.1:5000", "http://localhost:8000", "http://localhost:5000"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True,
         "max_age": 3600
     }
})

app.config.update(
    # Use 'Lax' for SameSite to allow cookies over HTTP during local development.
    # 'None' requires Secure=True in modern browsers which breaks localhost HTTP flow.
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=5)
)

# Store uploads under backend/uploads to keep files with the backend code
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# MongoDB
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/road_management"
mongo.init_app(app)

# Register routes
app.register_blueprint(routes)

# ------------ SERVE UPLOADS FOLDER ------------ #
@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded and detected files from uploads folder"""
    try:
        from flask import send_from_directory
        upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), 'uploads'))
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        logger.exception("Serve upload error")
        return jsonify({"error": "File not found"}), 404

# CORS headers helper for file uploads
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    allowed_origins = ['http://127.0.0.1:8000', 'http://127.0.0.1:5000', 'http://localhost:8000', 'http://localhost:5000']
    
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE, PUT'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response

# ---------------- BASIC ROUTES ---------------- #
@app.route("/")
def home():
    # If a frontend index.html exists, serve it. Otherwise return simple JSON.
    try:
        from flask import send_from_directory
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
    except Exception:
        pass
    return jsonify({"message": "Road Management API Running 🚦"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ---------------- USER / ADMIN LOGIN ---------------- #
@app.route("/send-otp", methods=["POST"])
def send_otp():
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"REQUEST RECEIVED: /send-otp [{timestamp}]", flush=True)
    data = request.get_json(silent=True) or {}
    print(f"Request body: {data}", flush=True)

    name = data.get("name")
    number = data.get("number")
    if not name or not number:
        error_response = {"error": "Name and number required"}
        print(f"REQUEST ERROR: missing name or number -> {error_response}", flush=True)
        return jsonify(error_response), 400

    otp = str(random.randint(1000, 9999))
    try:
        delete_result = mongo.db.otp_sessions.delete_many({"number": number})
        insert_result = mongo.db.otp_sessions.insert_one({
            "name": name,
            "number": number,
            "otp": otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=5)
        })
    except Exception as e:
        error_response = {"error": "Database write failed", "details": str(e)}
        print(f"DATABASE ERROR: {e}", flush=True)
        logger.exception("send-otp database error")
        return jsonify(error_response), 500

    print("\n" + "="*60, flush=True)
    print(f"TIMESTAMP: {timestamp}", flush=True)
    print(f"PHONE NUMBER: {number}", flush=True)
    print(f"GENERATED OTP: {otp}", flush=True)
    print(f"MongoDB insert id: {insert_result.inserted_id}", flush=True)
    print("="*60 + "\n", flush=True)

    otp_log_file = os.path.join(os.path.dirname(__file__), "otp_log.txt")
    try:
        with open(otp_log_file, "a") as f:
            f.write(f"\n[{timestamp}]\n")
            f.write(f"Name: {name}\n")
            f.write(f"Number: {number}\n")
            f.write(f"OTP: {otp}\n")
            f.write(f"Expires: {(datetime.utcnow() + timedelta(minutes=5)).strftime('%H:%M:%S')}\n")
            f.write("-" * 40 + "\n")
    except Exception as e:
        logger.exception("Failed to write OTP log file")
        print(f"OTP log write error: {e}", flush=True)

    response = {"message": "OTP Sent Successfully - Check terminal and otp_log.txt file"}
    print(f"Response returned: {response}", flush=True)
    logger.info("send-otp completed for %s", number)
    return jsonify(response)

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    data = request.get_json(silent=True) or {}
    number = data.get("number")
    otp = data.get("otp")

    print(f"REQUEST RECEIVED: /verify-otp [{timestamp}]", flush=True)
    print(f"Verifying OTP for number: {number}, otp: {otp}", flush=True)

    if not number or not otp:
        error_response = {"error": "Number and OTP required"}
        print(f"REQUEST ERROR: missing number or otp -> {error_response}", flush=True)
        logger.warning("verify-otp validation failed: %s", error_response)
        return jsonify(error_response), 400

    try:
        all_records = list(mongo.db.otp_sessions.find({"number": number}))
        print(f"   Found {len(all_records)} record(s) with this number in DB", flush=True)
        for rec in all_records:
            print(f"   DB record - OTP: {rec.get('otp')} (type: {type(rec.get('otp'))}), expires_at: {rec.get('expires_at')}", flush=True)

        record = mongo.db.otp_sessions.find_one({"number": number, "otp": otp})
    except Exception as e:
        logger.exception("verify-otp database error")
        error_response = {"error": "Database read failed", "details": str(e)}
        print(f"DATABASE ERROR: {e}", flush=True)
        return jsonify(error_response), 500

    if not record:
        print(f"   ❌ No matching record found!", flush=True)
        return jsonify({"error": "Invalid OTP"}), 400

    print(f"   ✅ OTP matched!", flush=True)

    if record["expires_at"] < datetime.utcnow():
        print(f"   ❌ OTP expired at {record['expires_at']}", flush=True)
        return jsonify({"error": "OTP Expired"}), 400

    print(f"   ✅ OTP valid, creating user session", flush=True)

    try:
        user = mongo.db.users.find_one({"number": number})
        if not user:
            mongo.db.users.insert_one({
                "name": record["name"],
                "number": number,
                "verified": True,
                "createdAt": datetime.utcnow()
            })
    except Exception as e:
        logger.exception("verify-otp failed to create user")
        error_response = {"error": "User creation failed", "details": str(e)}
        print(f"USER CREATION ERROR: {e}", flush=True)
        return jsonify(error_response), 500

    session.permanent = True
    session["role"] = "user"
    session["number"] = number
    response = {"message": "Login Successful"}
    print(f"Response returned: {response}", flush=True)
    logger.info("verify-otp succeeded for %s", number)
    return jsonify(response)

@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    admin = mongo.db.admins.find_one({"username": username})
    if not admin or not check_password_hash(admin["password"], password):
        logger.warning("admin-login failed for username: %s", username)
        return jsonify({"error": "Invalid Credentials"}), 401

    session.permanent = True
    session["role"] = "admin"
    return jsonify({"message": "Admin Login Successful"})

@app.route("/user-dashboard")
def user_dashboard():
    if session.get("role") != "user":
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"message": "Welcome User Dashboard 🚦"})

@app.route("/admin-dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    users = list(mongo.db.users.find({}, {"_id": 0}))
    return jsonify({"message": "Admin Dashboard 🛡️", "users": users})

@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# ---------------- DETECTION ROUTE ---------------- #
@app.route("/detect", methods=["POST"])
def detect():
    if session.get("role") != "user":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"status": "error", "message": "Invalid filename"}), 400

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS and ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"status": "error", "message": f"Unsupported file extension: {ext}"}), 400

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        file.save(save_path)
        logger.info("Uploaded filename: %s", filename)
        logger.info("Saved path: %s", save_path)
        logger.info("File exists after save: %s", os.path.exists(save_path))
        logger.info("File size bytes: %s", os.path.getsize(save_path))
    except Exception as e:
        logger.exception("File save error")
        return jsonify({"status": "error", "message": "Failed to save file", "details": str(e)}), 500

    try:
        result = detect_pothole(input_path=save_path, conf=0.25, save_output=True, output_folder=app.config["UPLOAD_FOLDER"])
        logger.info("Detection result: %s", result)
    except Exception as e:
        logger.exception("Detection error")
        return jsonify({"status": "error", "message": "AI detection failed", "details": str(e)}), 500

    if not isinstance(result, dict):
        return jsonify({"status": "error", "message": "Invalid detection result"}), 500

    if result.get('status') != 'ok':
        return jsonify(result), 400

    if "output_image" in result and result["output_image"]:
        result["output_image"] = "/uploads/" + os.path.basename(result["output_image"])
    if "output_video" in result and result["output_video"]:
        result["output_video"] = "/uploads/" + os.path.basename(result["output_video"])

    return jsonify(result)

# ---------------- RUN SERVER ---------------- #
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)