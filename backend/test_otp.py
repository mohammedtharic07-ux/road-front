import requests, re, time
s = requests.Session()
number = "+911234567890"
print('Sending OTP...')
r = s.post('http://127.0.0.1:5000/send-otp', json={'name':'TestUser','number':number}, timeout=10)
print('send status', r.status_code, r.text)
# wait briefly for log write
time.sleep(0.5)
try:
    with open('backend/otp_log.txt','r') as f:
        content = f.read()
except FileNotFoundError:
    with open('otp_log.txt','r') as f:
        content = f.read()
matches = re.findall(r'OTP: (\d+)', content)
if not matches:
    print('No OTP found in log')
    raise SystemExit(1)
otp = matches[-1]
print('Found OTP in log:', otp)
print('Verifying OTP...')
r2 = s.post('http://127.0.0.1:5000/verify-otp', json={'number':number,'otp':otp}, timeout=10)
print('verify status', r2.status_code, r2.text)
print('Cookies after verify:', s.cookies.get_dict())
print('Accessing dashboard...')
r3 = s.get('http://127.0.0.1:5000/user-dashboard', timeout=10)
print('dashboard status', r3.status_code, r3.text)
