import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
import json

print("🧪 Testing Detection with Flask Test Client\n" + "="*60)

# Create test client
with app.test_client() as client:
    # Simulate login by setting session data directly
    with client.session_transaction() as sess:
        sess['role'] = 'user'
        sess['number'] = '9999999999'
    
    # Test detection endpoint
    test_image_path = "uploads/img-335_jpg.rf.a4d865ebc23f3b7d06390c81e3424a33.jpg"
    
    if os.path.exists(test_image_path):
        print(f"✅ Testing with image: {test_image_path}\n")
        
        with open(test_image_path, 'rb') as img:
            response = client.post(
                '/detect-road-upload',
                data={'file': (img, test_image_path)},
                content_type='multipart/form-data'
            )
        
        print(f"📊 Status Code: {response.status_code}")
        data = json.loads(response.data)
        print(f"📊 Response:\n{json.dumps(data, indent=2)}\n")
        
        if response.status_code == 200:
            print("✅ DETECTION WORKING!")
            if data.get("detections", 0) > 0:
                print(f"✅ Found {data['detections']} pothole(s)")
            
            if data.get("output_image"):
                out_path = data["output_image"]
                exists = os.path.exists(out_path)
                print(f"✅ Output file: {out_path}")
                print(f"✅ File exists: {exists}")
                if exists:
                    size = os.path.getsize(out_path)
                    print(f"✅ File size: {size} bytes")
        else:
            print(f"❌ Error: {data.get('error')}")
    else:
        print(f"❌ Test image not found: {test_image_path}")

print("="*60)
