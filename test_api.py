from fastapi.testclient import TestClient
import sys
import os
import json

# Add project root to sys path
sys.path.append("/home/toobler/Desktop/Arjun/school_transport")

from backend.main import app

client = TestClient(app)

payload = {
    "scenario_id": 99,
    "event_payload": "Webhook: GPS indicates Bus AU-BUS-140 has deviated from the approved route by 2 miles.",
    "event_timestamp": "2026-06-10T12:00:00Z"
}

print("Testing POST /api/agents/supervisor/event with payload:")
print(json.dumps(payload, indent=2))

response = client.post("/api/agents/supervisor/event", json=payload)

print(f"\nStatus Code: {response.status_code}")
print("Response JSON:")
print(json.dumps(response.json(), indent=2))
