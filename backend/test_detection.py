import requests
import os
import json
from datetime import datetime

# Test the detection API
test_image = "uploads/path.jfif"
session = requests.Session()

# First, simulate login by setting session cookie
print("🔓 Simulating user session...")
session.cookies.set('session', 'test_session_' + str(datetime.now().timestamp()))

url = "http://127.0.0.1:5000/detect-road-upload"

if os.path.exists(test_image):
    print(f"✅ Testing detection with: {test_image}\n")
    
    with open(test_image, 'rb') as f:
        files = {'file': f}
        try:
            # Note: Session cookie may not work due to server-side validation
            # Let's check the actual error
            response = session.post(url, files=files, timeout=60)
            print(f"Status Code: {response.status_code}")
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
            
            # Check if output file exists
            if response.status_code == 200:
                data = response.json()
                if data.get("output_image"):
                    out_file = data.get("output_image")
                    print(f"\n✅ Output saved to: {out_file}")
                    print(f"✅ File exists: {os.path.exists(out_file)}")
                if data.get("detections", 0) > 0:
                    print(f"✅ Detections found: {data['detections']}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
else:
    print(f"❌ Test image not found: {test_image}")

print("\n" + "="*60)
print("Note: Frontend login is required for full testing")
print("="*60)
