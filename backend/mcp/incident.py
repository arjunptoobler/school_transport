import datetime
import uuid
import logging
from .base import mcp
from ..database.connection import get_db_connection

logger = logging.getLogger(__name__)


def _write_audit_log(conn, incident_id: str, agent: str, action: str, detail: str):
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO incident_audit_log (log_id, incident_id, agent, action, detail, timestamp) VALUES (?,?,?,?,?,?)",
        (log_id, incident_id, agent, action, detail, timestamp),
    )


def batch_write_history_to_audit_log(incident_id: str, history: list):
    """Write the entire scenario history to the audit log for a newly created incident."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for idx, step in enumerate(history):
            log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
            dt = datetime.datetime.now() - datetime.timedelta(seconds=len(history) - idx)
            agent = step.get("agent", "Unknown Agent")
            action = step.get("text", "") or step.get("action", "Analyzed Context")
            tool_name = step.get("tool", "Internal Logic")
            exec_action = step.get("action", "N/A")
            detail = f"{tool_name} → {exec_action}"
            cursor.execute(
                "INSERT INTO incident_audit_log (log_id, incident_id, agent, action, detail, timestamp) VALUES (?,?,?,?,?,?)",
                (log_id, incident_id, agent, action, detail, dt.isoformat()),
            )
        conn.commit()
    finally:
        conn.close()


@mcp.tool(name="mcp_create_incident")
def create_incident(severity: str, type: str, driver_id: str, vehicle_id: str, description: str, agent: str = "Incident Agent") -> dict:
    """File a compliance or safety incident in the master database and write the initial audit log entry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?)",
            (inc_id, severity, type, driver_id, vehicle_id, timestamp, description, "Detected", "None"),
        )
        _write_audit_log(conn, inc_id, agent, "Incident Created",
                         f"Severity={severity.upper()} · Type={type} · Driver={driver_id} · Vehicle={vehicle_id}")
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


@mcp.tool(name="mcp_get_open_incidents")
def get_open_incidents(limit: int = 20) -> list:
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


@mcp.tool(name="mcp_update_incident_status")
def update_incident_status(incident_id: str, status: str, agent: str = "System", reason: str = "") -> dict:
    """Update the event lifecycle status of an incident and write a timestamped audit entry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE incidents SET status = ? WHERE incident_id = ?", (status, incident_id))
        detail = f"Status changed to '{status}'" + (f" · Reason: {reason}" if reason else "")
        _write_audit_log(conn, incident_id, agent, "Status Updated", detail)
        conn.commit()
        return {"status": "success", "incident_id": incident_id, "new_status": status}
    finally:
        conn.close()


@mcp.tool(name="mcp_flag_for_manual_override")
def flag_for_manual_override(incident_id: str, reason: str, dispatcher_id: str = "CMD-CENTER-AUTO") -> dict:
    """Halt autonomous resolution and flag an incident for human-in-the-loop Command Center review."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE incidents SET status = 'Manual Override' WHERE incident_id = ?", (incident_id,))
        _write_audit_log(conn, incident_id, dispatcher_id, "Manual Override",
                         f"Autonomous workflow halted. Reason: {reason}")
        conn.commit()
        return {
            "status": "Halted Workflow",
            "incident_id": incident_id,
            "override_reason": reason,
            "dispatcher_id": dispatcher_id,
        }
    finally:
        conn.close()
