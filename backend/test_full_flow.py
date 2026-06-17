import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
import json

print("🧪 FULL DETECTION FLOW TEST")
print("=" * 70)

with app.test_client() as client:
    # Step 1: Simulate user login
    print("\n1️⃣ Simulating user login...")
    with client.session_transaction() as sess:
        sess['role'] = 'user'
        sess['number'] = '9999999999'
    print("   ✅ Session created")
    
    # Step 2: Upload and detect
    print("\n2️⃣ Uploading image for detection...")
    test_image = "uploads/img-335_jpg.rf.a4d865ebc23f3b7d06390c81e3424a33.jpg"
    
    if os.path.exists(test_image):
        with open(test_image, 'rb') as img:
            response = client.post(
                '/detect-road-upload',
                data={'file': (img, test_image)},
                content_type='multipart/form-data'
            )
        
        print(f"   Response Code: {response.status_code}")
        data = json.loads(response.data)
        print(f"   Response Data: {json.dumps(data, indent=6)}")
        
        if response.status_code == 200:
            print("\n   ✅ Detection API working!")
            
            # Step 3: Check API paths
            print("\n3️⃣ Checking returned paths...")
            if "output_image" in data:
                img_path = data["output_image"]
                print(f"   Image URL from API: {img_path}")
                
                # Step 4: Test file serving endpoint
                print("\n4️⃣ Testing file serving endpoint...")
                filename = os.path.basename(img_path.replace("/uploads/", ""))
                print(f"   Filename: {filename}")
                
                serve_response = client.get(f'/uploads/{filename}')
                print(f"   File serve status: {serve_response.status_code}")
                
                if serve_response.status_code == 200:
                    print(f"   File size: {len(serve_response.data)} bytes")
                    print("\n   ✅ File serving working!")
                else:
                    print(f"   ❌ File serve failed: {serve_response.status_code}")
                    
                # Step 5: Check actual file exists
                print("\n5️⃣ Checking file system...")
                full_path = "uploads/" + filename
                exists = os.path.exists(full_path)
                print(f"   Full path: {full_path}")
                print(f"   File exists: {exists}")
                if exists:
                    size = os.path.getsize(full_path)
                    print(f"   File size: {size} bytes")
                else:
                    print(f"   ❌ File not found at: {full_path}")
                    
        else:
            print(f"\n   ❌ Detection failed: {data}")
    else:
        print(f"   ❌ Test image not found: {test_image}")

print("\n" + "=" * 70)
print("\n📋 SUMMARY:")
print("   If all steps show ✅, detection is working end-to-end")
print("   If file serving shows ❌, frontend won't be able to display images")
