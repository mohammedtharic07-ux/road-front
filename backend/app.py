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
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

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
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

allowed_origins = [
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://localhost:5000",
]
netlify_frontend = os.environ.get("FRONTEND_URL")
if netlify_frontend:
    allowed_origins += [origin.strip() for origin in netlify_frontend.split(",") if origin.strip()]

# CORS configuration for cross-origin requests
CORS(app,
     resources={r"/*": {
         "origins": allowed_origins,
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
mongo_uri = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/road_management")
print("MONGO_URI =", os.getenv("MONGO_URI"))
if not isinstance(mongo_uri, str) or not mongo_uri.startswith(("mongodb://", "mongodb+srv://")):
    print("Invalid MONGO_URI detected. Falling back to default mongodb://127.0.0.1:27017/road_management")
    mongo_uri = "mongodb://127.0.0.1:27017/road_management"
app.config["MONGO_URI"] = mongo_uri
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
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    if not name or not email:
        error_response = {"error": "Name and email required"}
        logger.warning("send-otp validation failed: %s", error_response)
        return jsonify(error_response), 400

    otp = str(random.randint(1000, 9999))
    try:
        mongo.db.otp_sessions.delete_many({"email": email})
        insert_result = mongo.db.otp_sessions.insert_one({
            "name": name,
            "email": email,
            "otp": otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=5)
        })
    except Exception as e:
        error_response = {"error": "Database write failed", "details": str(e)}
        logger.exception("send-otp database error")
        return jsonify(error_response), 500

    # Send OTP via Gmail SMTP
    email_user = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASSWORD")
    if not email_user or not email_password:
        logger.error("Email credentials not configured in environment variables")
        return jsonify({"error": "Email server not configured"}), 500

    msg = EmailMessage()
    msg["Subject"] = "Your OTP Code"
    msg["From"] = email_user
    msg["To"] = email
    msg.set_content(f"Hello {name},\n\nYour OTP code is: {otp}\nThis code will expire in 5 minutes.\n\nIf you did not request this, please ignore this email.\n")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(email_user, email_password)
            smtp.send_message(msg)
    except Exception as e:
        logger.exception("Failed to send OTP email")
        return jsonify({"error": "Failed to send OTP email", "details": str(e)}), 500

    logger.info("send-otp completed for %s (db id: %s)", email, getattr(insert_result, 'inserted_id', None))
    return jsonify({"message": "OTP sent successfully. Check your email inbox."})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    otp = data.get("otp")

    logger.info("REQUEST RECEIVED: /verify-otp for %s", email)

    if not email or not otp:
        error_response = {"error": "Email and OTP required"}
        logger.warning("verify-otp validation failed: %s", error_response)
        return jsonify(error_response), 400

    try:
        all_records = list(mongo.db.otp_sessions.find({"email": email}))
        logger.info("Found %s OTP record(s) for email", len(all_records))
        record = mongo.db.otp_sessions.find_one({"email": email, "otp": otp})
    except Exception as e:
        logger.exception("verify-otp database error")
        return jsonify({"error": "Database read failed", "details": str(e)}), 500

    if not record:
        return jsonify({"error": "Invalid OTP"}), 400

    if record["expires_at"] < datetime.utcnow():
        return jsonify({"error": "OTP Expired"}), 400

    try:
        user = mongo.db.users.find_one({"email": email})
        if not user:
            mongo.db.users.insert_one({
                "name": record.get("name"),
                "email": email,
                "verified": True,
                "createdAt": datetime.utcnow()
            })
    except Exception as e:
        logger.exception("verify-otp failed to create user")
        return jsonify({"error": "User creation failed", "details": str(e)}), 500

    session.permanent = True
    session["role"] = "user"
    session["email"] = email
    logger.info("verify-otp succeeded for %s", email)
    return jsonify({"message": "Login Successful"})

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