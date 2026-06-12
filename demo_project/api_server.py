#!/usr/bin/env python3
"""api_server.py — API服务 (正官·法度调度)"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from src.data_store import query_records, count_records
import json

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond({"status": "ok"})
        elif self.path == "/records":
            self._respond({"records": query_records(), "count": count_records()})
        else:
            self._respond({"error": "not found"}, code=404)

    def _respond(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), APIHandler)
    print("API Server running on :8080")
    server.serve_forever()
