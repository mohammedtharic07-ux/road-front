from detect_debug import detect_pothole

path = 'backend/uploads/download_3.jfif'
print('Testing detect_pothole on', path)
res = detect_pothole(input_path=path, conf=0.15, save_output=True, output_folder='../uploads')
print('Result:', res)
