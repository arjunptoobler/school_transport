import datetime
import uuid
from .base import mcp_registry
from ..database.connection import get_db_connection

@mcp_registry.register_tool(name="mcp_create_incident")
def create_incident(severity: str, type: str, driver_id: str, vehicle_id: str, description: str):
    """File a compliance or safety incident event inside the master SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?,?)", 
                   (inc_id, severity, type, driver_id, vehicle_id, timestamp, description))
    conn.commit()
    conn.close()
    return {
        "success": True, 
        "incident_id": inc_id, 
        "severity": severity, 
        "type": type,
        "driver_id": driver_id,
        "vehicle_id": vehicle_id,
        "timestamp": timestamp
    }

@mcp_registry.register_tool(name="mcp_get_open_incidents")
def get_open_incidents(limit: int = 20):
    """Query recent incident records sorted chronologically."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "incident_id": r["incident_id"],
            "severity": r["severity"],
            "type": r["type"],
            "driver_id": r["driver_id"],
            "vehicle_id": r["vehicle_id"],
            "timestamp": r["timestamp"],
            "description": r["description"]
        } for r in rows
    ]
