"""
Simple HTTP server to serve frontend files
Avoids CORS issues when opening files directly
Run: python frontend_server.py
Then open: http://127.0.0.1:8000/login.html
"""

from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

os.chdir('d:\\Tharic\\project\\frontend')

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def log_message(self, format, *args):
        # Log requests
        if '%' in format:
            print(f"[Frontend Server] {format % args}")

PORT = 8000
server_address = ('127.0.0.1', PORT)
httpd = HTTPServer(server_address, MyHTTPRequestHandler)

print(f"🚀 Frontend server running at: http://127.0.0.1:{PORT}")
print(f"   Login page: http://127.0.0.1:{PORT}/login.html")
print(f"   Dashboard: http://127.0.0.1:{PORT}/index.html")
print(f"   Backend API: http://127.0.0.1:5000")
print(f"\nPress Ctrl+C to stop\n")

httpd.serve_forever()
