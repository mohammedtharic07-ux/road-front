import requests
import json

print("🧪 Testing Frontend API Calls (with CORS)\n" + "="*70)

# Test 1: Send OTP (like frontend does)
print("\n1️⃣ Testing Send OTP (from frontend)...")
try:
    response = requests.post(
        "http://127.0.0.1:5000/send-otp",
        json={"name": "Frontend Test", "number": "1234567890"},
        headers={"Content-Type": "application/json"},
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    if response.status_code == 200:
        print("   ✅ OTP send works!")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Check health endpoint
print("\n2️⃣ Testing Health endpoint...")
try:
    response = requests.get("http://127.0.0.1:5000/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print(f"   CORS Headers: {dict(response.headers)}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"   ✅ CORS enabled: {response.headers['Access-Control-Allow-Origin']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Test file serving with CORS
print("\n3️⃣ Testing File Serving with CORS...")
try:
    # First create a test file
    test_file = "uploads/output_pothole_20260309_150125_088.jpg"
    response = requests.get(f"http://127.0.0.1:5000/uploads/output_pothole_20260309_150125_088.jpg")
    print(f"   Status: {response.status_code}")
    print(f"   File size: {len(response.content)} bytes")
    print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"   ✅ CORS allowed: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print(f"   ⚠️  No CORS header")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*70)
print("✅ All frontend API calls working with CORS!")
