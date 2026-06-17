from flask import Blueprint, request, jsonify, session, current_app
from db import mongo
from bson import ObjectId
from bson.errors import InvalidId
from detect import detect_pothole
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import random

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

routes = Blueprint("routes", __name__)

# ---------------------------
# LOGIN CHECK HELPER
# ---------------------------
def require_login():
    return session.get("role") in ["admin", "user"]

# ---------------------------
# ADD ROAD
# ---------------------------
@routes.route("/add-road", methods=["POST"])
def add_road():
    if not require_login():
        return jsonify({"error": "Login required"}), 403

    data = request.json or {}
    required = ["roadName", "area", "condition"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    road = {
        "roadName": data["roadName"],
        "area": data["area"],
        "condition": data["condition"],
        "createdBy": session.get("role"),
        "createdAt": datetime.utcnow()
    }

    mongo.db.roads.insert_one(road)
    return jsonify({"message": "Road Added Successfully"}), 201

# ---------------------------
# REPORT ISSUE
# ---------------------------
@routes.route("/report-issue", methods=["POST"])
def report_issue():
    if not require_login():
        return jsonify({"error": "Login required"}), 403

    data = request.json or {}
    required = ["roadId", "issueType", "severity", "description"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    try:
        road = mongo.db.roads.find_one({"_id": ObjectId(data["roadId"])})
        if not road:
            return jsonify({"error": "Invalid road ID"}), 404
    except InvalidId:
        return jsonify({"error": "Invalid road ID format"}), 400

    issue = {
        "roadId": data["roadId"],
        "issueType": data["issueType"],
        "severity": data["severity"],
        "description": data["description"],
        "status": "pending",
        "reportedBy": session.get("role"),
        "createdAt": datetime.utcnow()
    }

    mongo.db.issues.insert_one(issue)
    return jsonify({"message": "Issue reported successfully 🕳️"}), 201

# ---------------------------
# GET ROADS
# ---------------------------
@routes.route("/roads", methods=["GET"])
def get_roads():
    if not require_login():
        return jsonify({"error": "Login required"}), 403

    roads = list(mongo.db.roads.find())
    for r in roads:
        r["_id"] = str(r["_id"])
    return jsonify(roads), 200

# ---------------------------
# DELETE ROAD (ADMIN)
# ---------------------------
@routes.route("/delete-road/<id>", methods=["DELETE"])
def delete_road(id):
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    try:
        result = mongo.db.roads.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Road not found"}), 404
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    return jsonify({"message": "Road deleted successfully"}), 200

# ---------------------------
# LOGOUT
# ---------------------------
@routes.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# ---------------------------
# USER DASHBOARD CHECK
# ---------------------------
@routes.route("/user-dashboard", methods=["GET"])
def user_dashboard():
    if not require_login():
        return jsonify({"error": "Login required"}), 403
    return jsonify({"message": "User dashboard", "role": session.get("role")}), 200

# ---------------------------
# ADMIN DASHBOARD CHECK
# ---------------------------
@routes.route("/admin-dashboard", methods=["GET"])
def admin_dashboard():
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return jsonify({"message": "Admin dashboard", "role": "admin"}), 200

# ---------------------------
# AI ROAD DETECTION
# ---------------------------
@routes.route("/detect-road-upload", methods=["POST"])
def detect_road_upload_api():
    if not require_login():
        return jsonify({"error": "Login required"}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"status": "error", "message": "Invalid filename"}), 400

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"status": "error", "message": f"Unsupported file extension: {ext}"}), 400

    save_path = os.path.join(upload_folder, filename)

    try:
        file.save(save_path)
        print("Uploaded filename:", filename)
        print("Saved path:", save_path)
        print("File exists after save:", os.path.exists(save_path))
        print("File size bytes:", os.path.getsize(save_path))
    except Exception as e:
        print("File save error:", e)
        return jsonify({"status": "error", "message": "Failed to save file", "details": str(e)}), 500

    try:
        result = detect_pothole(input_path=save_path, conf=0.15, save_output=True, output_folder=upload_folder)
        print("Detection result:", result)
    except Exception as e:
        print("Detection error:", e)
        return jsonify({"status": "error", "message": "AI detection failed", "details": str(e)}), 500

    if not isinstance(result, dict):
        return jsonify({"status": "error", "message": "Invalid detection result"}), 500

    if result.get('status') != 'ok':
        return jsonify(result), 400

    if "output_image" in result and result["output_image"]:
        result["output_image"] = "/uploads/" + os.path.basename(result["output_image"])
    if "output_video" in result and result["output_video"]:
        result["output_video"] = "/uploads/" + os.path.basename(result["output_video"])

    if result.get("status") == "ok" and result.get("detections", 0) > 0:
        issue = {
            "roadId": "AUTO",
            "issueType": f"AI Detected Damage ({result.get('type', 'file')})",
            "severity": "medium",
            "description": f"{result['detections']} potholes detected",
            "status": "pending",
            "createdAt": datetime.utcnow(),
            "reportedBy": session.get("role")
        }
        try:
            mongo.db.issues.insert_one(issue)
        except Exception as e:
            print("DB insert error:", e)

    return jsonify(result), 200

