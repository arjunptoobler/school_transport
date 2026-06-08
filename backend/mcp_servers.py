import sqlite3
import os
from .database import DB_PATH
from .rag import query_policy

# --- 1. Policy MCP Server ---
class PolicyMCPServer:
    @staticmethod
    def lookup_policy(topic: str):
        """Query policy regulations via vector RAG layer."""
        return query_policy(topic)

    @staticmethod
    def get_violation_matrix():
        """Retrieve standard violation categories and fine metrics."""
        return {
            "driver_distraction": {"fine_aed": 5000, "black_points": 24, "action": "Immediate Suspension"},
            "speeding_school_zone": {"fine_aed": 3000, "black_points": 12, "action": "Warning / Retraining"},
            "missing_guardian": {"fine_aed": 0, "black_points": 0, "action": "Retain pupil and contact parent"}
        }

# --- 2. Fleet MCP Server ---
class FleetMCPServer:
    @staticmethod
    def get_vehicle_status(vehicle_id: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "vehicle_id": row[0],
                "license_plate": row[1],
                "age": row[2],
                "gps_status": row[3],
                "inspection_status": row[4]
            }
        return {"error": "Vehicle not found"}

    @staticmethod
    def update_inspection_status(vehicle_id: str, status: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET inspection_status = ? WHERE vehicle_id = ?", (status, vehicle_id))
        conn.commit()
        conn.close()
        return {"success": True, "vehicle_id": vehicle_id, "inspection_status": status}

# --- 3. Driver MCP Server ---
class DriverMCPServer:
    @staticmethod
    def get_driver_record(driver_id: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers WHERE driver_id = ?", (driver_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "driver_id": row[0],
                "name": row[1],
                "permit_status": row[2],
                "medical_status": row[3],
                "training_status": row[4],
                "operator": row[5]
            }
        return {"error": "Driver not found"}

    @staticmethod
    def update_driver_status(driver_id: str, permit_status: str, training_status: str = None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if training_status:
            cursor.execute("UPDATE drivers SET permit_status = ?, training_status = ? WHERE driver_id = ?", (permit_status, training_status, driver_id))
        else:
            cursor.execute("UPDATE drivers SET permit_status = ? WHERE driver_id = ?", (permit_status, driver_id))
        conn.commit()
        conn.close()
        return {"success": True, "driver_id": driver_id, "permit_status": permit_status}

# --- 4. Notification MCP Server ---
class NotificationMCPServer:
    @staticmethod
    def send_sms(recipient: str, message: str):
        # In a real environment, this connects to Twilio / Etisalat SMS gateway
        print(f"[SMS Gateway] Sent to {recipient}: {message}")
        return {"status": "sent", "recipient": recipient, "channel": "SMS"}

    @staticmethod
    def send_push(recipient: str, title: str, message: str):
        # Real push notification server
        print(f"[Push Service] Sent to {recipient} [{title}]: {message}")
        return {"status": "sent", "recipient": recipient, "channel": "Push"}

# --- 5. Incident MCP Server ---
class IncidentMCPServer:
    @staticmethod
    def create_incident(incident_id: str, severity: str, inc_type: str, driver_id: str, vehicle_id: str, description: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?,?)", 
                       (incident_id, severity, inc_type, driver_id, vehicle_id, timestamp, description))
        conn.commit()
        conn.close()
        return {
            "success": True, 
            "incident_id": incident_id, 
            "severity": severity, 
            "type": inc_type,
            "driver_id": driver_id,
            "vehicle_id": vehicle_id
        }

    @staticmethod
    def get_open_incidents():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "incident_id": r[0],
                "severity": r[1],
                "type": r[2],
                "driver_id": r[3],
                "vehicle_id": r[4],
                "timestamp": r[5],
                "description": r[6]
            } for r in rows
        ]
