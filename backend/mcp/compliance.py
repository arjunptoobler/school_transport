from datetime import datetime, timedelta
from .base import mcp_registry
from ..database.connection import get_db_connection

@mcp_registry.register_tool(name="mcp_issue_fine_ticket")
def issue_fine_ticket(driver_id: str, vehicle_id: str, violation_type: str, amount: float, authority: str = "DMT"):
    """Issue a fine ticket to a driver for a safety or compliance violation. Authority can be DMT or ADEK."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Find next fine ID
        cursor.execute("SELECT COUNT(*) FROM fines")
        count = cursor.fetchone()[0]
        fine_id = f"FINE-{2001 + count}"
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO fines (fine_id, driver_id, vehicle_id, violation_type, amount, authority, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fine_id, driver_id, vehicle_id, violation_type, amount, authority, timestamp))
        conn.commit()
        return {
            "status": "success",
            "fine_id": fine_id,
            "driver_id": driver_id,
            "violation_type": violation_type,
            "amount": amount,
            "authority": authority,
            "timestamp": timestamp
        }
    finally:
        conn.close()

@mcp_registry.register_tool(name="mcp_assign_training_sla")
def assign_training_sla(driver_id: str, incident_id: str):
    """Assign mandatory training to a driver with a strict 5-day SLA timeline."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM compliance_sla")
        count = cursor.fetchone()[0]
        sla_id = f"SLA-{3001 + count}"
        
        assigned_date = datetime.now()
        deadline_date = assigned_date + timedelta(days=5)
        
        cursor.execute("""
            INSERT INTO compliance_sla (sla_id, driver_id, incident_id, assigned_date, deadline_date, status, resolution_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sla_id, driver_id, incident_id, assigned_date.isoformat(), deadline_date.isoformat(), "Pending", None))
        
        # Also mark training status as Pending Refresher in driver record
        cursor.execute("UPDATE drivers SET training_status = 'Pending Refresher' WHERE driver_id = ?", (driver_id,))
        conn.commit()
        
        return {
            "status": "success",
            "sla_id": sla_id,
            "driver_id": driver_id,
            "deadline": deadline_date.isoformat(),
            "sla_days": 5
        }
    finally:
        conn.close()

@mcp_registry.register_tool(name="mcp_check_sla_compliance")
def check_sla_compliance():
    """Verify SLA deadlines. If any training SLA exceeds the 5-day window, automatically recommend suspension."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        
        # Select all pending SLAs past deadline
        cursor.execute("""
            SELECT sla_id, driver_id, deadline_date FROM compliance_sla 
            WHERE status = 'Pending' AND deadline_date < ?
        """, (now_str,))
        overdue_slas = cursor.fetchall()
        
        escalations = []
        for sla in overdue_slas:
            sla_id, drv_id, deadline = sla
            # Auto-suspend driver permit
            cursor.execute("UPDATE drivers SET permit_status = 'Suspended' WHERE driver_id = ?", (drv_id,))
            cursor.execute("UPDATE compliance_sla SET status = 'Escalated' WHERE sla_id = ?", (sla_id,))
            escalations.append({
                "sla_id": sla_id,
                "driver_id": drv_id,
                "deadline": deadline,
                "action": "Permit suspended automatically due to 5-day SLA breach."
            })
            
        if overdue_slas:
            conn.commit()
            
        return {
            "status": "success",
            "checked_at": now_str,
            "escalation_count": len(escalations),
            "escalations": escalations
        }
    finally:
        conn.close()

@mcp_registry.register_tool(name="mcp_ingest_edge_telemetry")
def ingest_edge_telemetry(vehicle_id: str, event_type: str, confidence: float, gforce_x: float = 0.0, gforce_y: float = 0.0, gforce_z: float = 0.0, evidence_url: str = ""):
    """Ingest real-time ADAS edge telemetry data and trigger incident creation if confidence exceeds 0.8."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM edge_telemetry")
        count = cursor.fetchone()[0]
        event_id = f"EVT-{4001 + count}"
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO edge_telemetry (event_id, vehicle_id, event_type, confidence, gforce_x, gforce_y, gforce_z, evidence_url, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, vehicle_id, event_type, confidence, gforce_x, gforce_y, gforce_z, evidence_url, timestamp))
        
        incident_triggered = False
        incident_id = None
        
        if confidence >= 0.8:
            # Auto-trigger incident creation
            cursor.execute("SELECT COUNT(*) FROM incidents")
            inc_count = cursor.fetchone()[0]
            incident_id = f"INC-2026-{1001 + inc_count:04d}"
            
            # Find active driver for vehicle
            cursor.execute("SELECT driver_id FROM drivers LIMIT 1") # fallback active driver
            row = cursor.fetchone()
            driver_id = row["driver_id"] if row else "Unknown"
            
            severity = "high" if event_type in ["Collision", "Phone_Usage"] else "med"
            desc = f"Edge AI detected {event_type} event on bus {vehicle_id} with {confidence*100:.1f}% confidence. Evidence: {evidence_url}"
            
            cursor.execute("""
                INSERT INTO incidents (incident_id, severity, type, driver_id, vehicle_id, timestamp, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (incident_id, severity, event_type, driver_id, vehicle_id, timestamp, desc))
            incident_triggered = True
            
        conn.commit()
        return {
            "status": "success",
            "event_id": event_id,
            "incident_triggered": incident_triggered,
            "incident_id": incident_id,
            "timestamp": timestamp
        }
    finally:
        conn.close()
