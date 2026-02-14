from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "active",
            "message": "Gmail Warmup Service is running",
            "usage": "GET /api/warmup to trigger manually"
        }).encode('utf-8'))
