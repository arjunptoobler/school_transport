import datetime
import uuid
from .base import mcp_registry
from ..database.connection import get_db_connection


@mcp_registry.register_tool(name="mcp_create_incident")
def create_incident(severity: str, type: str, driver_id: str, vehicle_id: str, description: str):
    """File a compliance or safety incident event inside the master SQLite database with a lifecycle status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?)",
            (inc_id, severity, type, driver_id, vehicle_id, timestamp, description, "Detected"),
        )
        conn.commit()
        return {
            "success": True,
            "incident_id": inc_id,
            "severity": severity,
            "type": type,
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "timestamp": timestamp,
            "status": "Detected",
        }
    finally:
        conn.close()


@mcp_registry.register_tool(name="mcp_get_open_incidents")
def get_open_incidents(limit: int = 20):
    """Query recent incident records sorted chronologically including their lifecycle status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [
            {
                "incident_id": r["incident_id"],
                "severity": r["severity"],
                "type": r["type"],
                "driver_id": r["driver_id"],
                "vehicle_id": r["vehicle_id"],
                "timestamp": r["timestamp"],
                "description": r["description"],
                "status": r["status"] if "status" in r.keys() else "Detected",
            }
            for r in rows
        ]
    finally:
        conn.close()


@mcp_registry.register_tool(name="mcp_update_incident_status")
def update_incident_status(incident_id: str, status: str):
    """Update the event lifecycle status of a safety or compliance incident (e.g. Detected, Validation, Notification, Investigation, Resolution, Reporting)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE incidents SET status = ? WHERE incident_id = ?", (status, incident_id))
        conn.commit()
        return {"status": "success", "incident_id": incident_id, "new_status": status}
    finally:
        conn.close()


@mcp_registry.register_tool(name="mcp_flag_for_manual_override")
def flag_for_manual_override(incident_id: str, reason: str, dispatcher_id: str = "CMD-CENTER-AUTO") -> dict:
    """
    Halts autonomous resolution for an incident and flags it for immediate human-in-the-loop (Command Center) review.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE incidents SET status = 'Manual Override' WHERE incident_id = ?", (incident_id,))
        conn.commit()
        return {
            "status": "Halted Workflow",
            "incident_id": incident_id,
            "override_reason": reason,
            "dispatcher_id": dispatcher_id
        }
    finally:
        conn.close()
