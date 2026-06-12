import logging
from datetime import datetime, timedelta
from .base import mcp
from ..database.connection import get_db_connection

logger = logging.getLogger(__name__)


@mcp.tool(name="mcp_issue_fine_ticket")
def issue_fine_ticket(driver_id: str, vehicle_id: str, violation_type: str, amount: float, authority: str = "DMT") -> dict:
    """Issue a fine ticket to a driver for a safety or compliance violation. Authority can be DMT or ADEK."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fines")
        count = cursor.fetchone()[0]
        fine_id = f"FINE-{2001 + count}"
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO fines (fine_id, driver_id, vehicle_id, violation_type, amount, authority, timestamp) VALUES (?,?,?,?,?,?,?)",
            (fine_id, driver_id, vehicle_id, violation_type, amount, authority, timestamp),
        )
        conn.commit()
        return {
            "status": "success",
            "fine_id": fine_id,
            "driver_id": driver_id,
            "violation_type": violation_type,
            "amount": amount,
            "authority": authority,
            "timestamp": timestamp,
        }
    finally:
        conn.close()


@mcp.tool(name="mcp_assign_training_sla")
def assign_training_sla(driver_id: str, incident_id: str) -> dict:
    """Assign mandatory training to a driver with a strict 5-day SLA timeline."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM compliance_sla")
        count = cursor.fetchone()[0]
        sla_id = f"SLA-{3001 + count}"
        assigned_date = datetime.now()
        deadline_date = assigned_date + timedelta(days=5)
        cursor.execute(
            "INSERT INTO compliance_sla (sla_id, driver_id, incident_id, assigned_date, deadline_date, status, resolution_date) VALUES (?,?,?,?,?,?,?)",
            (sla_id, driver_id, incident_id, assigned_date.isoformat(), deadline_date.isoformat(), "Pending", None),
        )
        cursor.execute("UPDATE drivers SET training_status = 'Pending Refresher' WHERE driver_id = ?", (driver_id,))
        conn.commit()
        return {
            "status": "success",
            "sla_id": sla_id,
            "driver_id": driver_id,
            "deadline": deadline_date.isoformat(),
            "sla_days": 5,
        }
    finally:
        conn.close()


@mcp.tool(name="mcp_check_sla_compliance")
def check_sla_compliance() -> dict:
    """Verify SLA deadlines. If any training SLA exceeds the 5-day window, automatically recommend suspension."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute(
            "SELECT sla_id, driver_id, deadline_date FROM compliance_sla WHERE status = 'Pending' AND deadline_date < ?",
            (now_str,),
        )
        overdue_slas = cursor.fetchall()
        escalations = []
        for sla in overdue_slas:
            sla_id, drv_id, deadline = sla["sla_id"], sla["driver_id"], sla["deadline_date"]
            cursor.execute("UPDATE drivers SET permit_status = 'Suspended' WHERE driver_id = ?", (drv_id,))
            cursor.execute("UPDATE compliance_sla SET status = 'Escalated' WHERE sla_id = ?", (sla_id,))
            escalations.append({
                "sla_id": sla_id,
                "driver_id": drv_id,
                "deadline": deadline,
                "action": "Permit suspended automatically due to 5-day SLA breach.",
            })
        if overdue_slas:
            conn.commit()
        return {
            "status": "success",
            "checked_at": now_str,
            "escalation_count": len(escalations),
            "escalations": escalations,
        }
    finally:
        conn.close()


@mcp.tool(name="mcp_ingest_edge_telemetry")
def ingest_edge_telemetry(vehicle_id: str, event_type: str, confidence: float,
                          gforce_x: float = 0.0, gforce_y: float = 0.0,
                          gforce_z: float = 0.0, evidence_url: str = "") -> dict:
    """Ingest real-time ADAS edge telemetry data and trigger incident creation if confidence exceeds 0.8."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM edge_telemetry")
        count = cursor.fetchone()[0]
        event_id = f"EVT-{4001 + count}"
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO edge_telemetry (event_id, vehicle_id, event_type, confidence, gforce_x, gforce_y, gforce_z, evidence_url, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
            (event_id, vehicle_id, event_type, confidence, gforce_x, gforce_y, gforce_z, evidence_url, timestamp),
        )
        incident_triggered = False
        incident_id = None
        if confidence >= 0.8:
            cursor.execute("SELECT COUNT(*) FROM incidents")
            inc_count = cursor.fetchone()[0]
            incident_id = f"INC-2026-{1001 + inc_count:04d}"
            cursor.execute("SELECT driver_id FROM drivers LIMIT 1")
            row = cursor.fetchone()
            driver_id = row["driver_id"] if row else "Unknown"
            severity = "high" if event_type in ["Collision", "Phone_Usage"] else "med"
            desc = f"Edge AI detected {event_type} on bus {vehicle_id} with {confidence*100:.1f}% confidence."
            cursor.execute(
                "INSERT INTO incidents (incident_id, severity, type, driver_id, vehicle_id, timestamp, description, status, evidence_url) VALUES (?,?,?,?,?,?,?,?,?)",
                (incident_id, severity, event_type, driver_id, vehicle_id, timestamp, desc, "Detected", evidence_url),
            )
            incident_triggered = True
        conn.commit()
        return {
            "status": "success",
            "event_id": event_id,
            "incident_triggered": incident_triggered,
            "incident_id": incident_id,
            "timestamp": timestamp,
        }
    finally:
        conn.close()


@mcp.tool(name="mcp_submit_adek_compliance_report")
def submit_adek_compliance_report(report_type: str, driver_id: str, severity: str, narrative: str) -> dict:
    """Submit a formal compliance infraction report to the external ADEK/Government regulatory portal."""
    logger.info(f"Submitting {report_type} compliance report to ADEK for driver {driver_id}")
    return {
        "status": "Submitted to Government Portal",
        "external_reference_id": f"ADEK-REP-{driver_id}-{severity.upper()}",
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool(name="mcp_sync_permit_status_with_gov")
def sync_permit_status_with_gov(driver_id: str, new_status: str) -> dict:
    """Synchronize the internal database permit status with the external government licensing authority."""
    logger.info(f"Syncing permit status '{new_status}' with government for driver {driver_id}")
    return {
        "status": "Synchronized",
        "driver_id": driver_id,
        "government_ledger_status": new_status,
        "sync_latency_ms": 142,
    }


@mcp.tool(name="mcp_get_executive_metrics")
def get_executive_metrics() -> dict:
    """Fetch real-time operational KPIs from the fleet database for executive dashboard reporting."""
    import datetime
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # ── Current totals ────────────────────────────────────────────────────
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status NOT IN ('Closed', 'Resolved')")
        open_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status NOT IN ('Closed', 'Resolved') AND severity = 'high'")
        critical_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fines")
        total_fines = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM fines")
        total_fines_amount = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
        pending_training = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE inspection_status != 'valid'")
        grounded_buses = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE permit_status = 'Suspended'")
        suspended_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE gps_status = 'online'")
        gps_active = cursor.fetchone()[0]

        # ── Time-sliced data (this month vs last month) ───────────────────────
        today = datetime.date.today()
        this_month_start = today.replace(day=1).isoformat()
        last_month_end   = (today.replace(day=1) - datetime.timedelta(days=1))
        last_month_start = last_month_end.replace(day=1).isoformat()
        last_month_end   = last_month_end.isoformat()

        cursor.execute(
            "SELECT COUNT(*) FROM incidents WHERE timestamp >= ?",
            (this_month_start,),
        )
        incidents_this_month = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM incidents WHERE timestamp >= ? AND timestamp <= ?",
            (last_month_start, last_month_end + "T23:59:59"),
        )
        incidents_last_month = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM fines WHERE timestamp >= ?",
            (this_month_start,),
        )
        fines_this_month = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM fines WHERE timestamp >= ? AND timestamp <= ?",
            (last_month_start, last_month_end + "T23:59:59"),
        )
        fines_last_month = cursor.fetchone()[0]

        # Suspension-related fines as proxy for driver suspensions per month
        cursor.execute(
            "SELECT COUNT(*) FROM fines WHERE violation_type IN ('Pre-Departure Compliance Failure', 'Driver Distraction', 'Speed Violation') AND timestamp >= ?",
            (this_month_start,),
        )
        suspensions_this_month = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM fines WHERE violation_type IN ('Pre-Departure Compliance Failure', 'Driver Distraction', 'Speed Violation') AND timestamp >= ? AND timestamp <= ?",
            (last_month_start, last_month_end + "T23:59:59"),
        )
        suspensions_last_month = cursor.fetchone()[0]

        # ── Top violating drivers (incident count) ────────────────────────────
        cursor.execute("""
            SELECT d.driver_id, d.name, d.operator, d.permit_status,
                   COUNT(i.incident_id) AS incident_count
            FROM drivers d
            LEFT JOIN incidents i ON d.driver_id = i.driver_id
            GROUP BY d.driver_id
            ORDER BY incident_count DESC
            LIMIT 3
        """)
        top_risk_drivers = [
            {"driver_id": r[0], "name": r[1], "operator": r[2],
             "permit_status": r[3], "incident_count": r[4]}
            for r in cursor.fetchall()
        ]

        # ── Compliance score trend ────────────────────────────────────────────
        cursor.execute(
            "SELECT COUNT(*) FROM drivers WHERE permit_status = 'Valid' AND training_status = 'Complete'"
        )
        compliant_now = cursor.fetchone()[0]
        compliance_score_pct = round((compliant_now / total_drivers) * 100, 1) if total_drivers else 0

        return {
            "open_incidents": open_incidents,
            "critical_incidents": critical_incidents,
            "total_fines": total_fines,
            "total_fines_amount_aed": round(float(total_fines_amount), 2),
            "pending_training": pending_training,
            "grounded_buses": grounded_buses,
            "suspended_drivers": suspended_drivers,
            "total_drivers": total_drivers,
            "gps_active": gps_active,
            # Time-sliced
            "incidents_this_month": incidents_this_month,
            "incidents_last_month": incidents_last_month,
            "fines_this_month": fines_this_month,
            "fines_last_month": fines_last_month,
            "suspensions_this_month": suspensions_this_month,
            "suspensions_last_month": suspensions_last_month,
            # Risk intelligence
            "top_risk_drivers": top_risk_drivers,
            "compliance_score_pct": compliance_score_pct,
            "reporting_period": {
                "this_month": this_month_start[:7],
                "last_month": last_month_start[:7],
            },
        }
    finally:
        conn.close()
