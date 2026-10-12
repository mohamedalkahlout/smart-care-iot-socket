"""
Lightweight REST API Gateway for Caregiver Dashboard & Sockets
Smart Care IoT Socket (Retrofit Edge-AI & Safety Guard)

Provides endpoints:
- POST /api/nlp/command  : Schema-enforced natural language command parsing.
- GET  /api/telemetry    : Retrieve recent telemetry records.
- POST /api/telemetry    : Ingest telemetry record into structured storage.
- GET  /api/health       : System health and version check.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Ensure local imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cloud.nlp_assistant import ConstrainedNlpAssistant
from cloud.telemetry_logger import TelemetryLogger

# Global singletons
nlp_assistant = ConstrainedNlpAssistant()
telemetry_logger = TelemetryLogger(
    max_buffer_size=1000,
    log_file=os.path.join(os.path.dirname(__file__), "telemetry_log.jsonl")
)


class SmartSocketApiHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(200, {
                "status": "healthy",
                "service": "Smart Care Socket Gateway",
                "version": "1.0.0",
                "schema_enforced": True
            })
        elif parsed.path == "/api/telemetry":
            records = telemetry_logger.query_recent(limit=50)
            self._send_json(200, {
                "count": len(records),
                "records": records
            })
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            self._send_json(400, {"error": "Malformed JSON payload"})
            return

        if parsed.path == "/api/nlp/command":
            res = nlp_assistant.process_api_request(payload)
            status_code = 200 if res.get("success") else 422
            self._send_json(status_code, res)

        elif parsed.path == "/api/telemetry":
            record = telemetry_logger.ingest_dict(payload)
            self._send_json(201, {
                "success": True,
                "message": "Telemetry logged successfully",
                "device_id": record.device_id,
                "ts": record.ts
            })

        else:
            self._send_json(404, {"error": "Endpoint not found"})


def run_server(port: int = 8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, SmartSocketApiHandler)
    print(f"[*] Smart Socket Gateway running on http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Stopping server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
