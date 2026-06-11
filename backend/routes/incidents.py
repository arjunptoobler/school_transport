import datetime
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database.connection import get_db_connection

router = APIRouter(prefix="/incidents", tags=["Incident Management"])


class IncidentCreate(BaseModel):
    severity: str
    type: str
    driver_id: str
    vehicle_id: str
    description: str
    evidence_url: str = "None"


@router.get("/")
def get_incidents():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT 20")
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/simulate")
def simulate_incident(req: IncidentCreate):
    conn = get_db_connection()
    try:
        inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.datetime.now().isoformat()

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?)",
            (inc_id, req.severity, req.type, req.driver_id, req.vehicle_id, timestamp, req.description, "Detected", req.evidence_url),
        )
        conn.commit()

        return {
            "success": True,
            "incident": {
                "incident_id": inc_id,
                "severity": req.severity,
                "type": req.type,
                "driver_id": req.driver_id,
                "vehicle_id": req.vehicle_id,
                "timestamp": timestamp,
                "description": req.description,
                "status": "Detected",
                "evidence_url": req.evidence_url,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/charts")
def get_charts_data():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Violation Breakdown (Doughnut Chart)
        cursor.execute("SELECT type, COUNT(*) as count FROM incidents GROUP BY type")
        violations = cursor.fetchall()
        violation_labels = []
        violation_data = []
        for v in violations:
            violation_labels.append(v["type"])
            violation_data.append(v["count"])

        # 2. Risk Matrix (Radar Chart)
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'high'")
        high_risk = cursor.fetchone()[0] * 10
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'med'")
        med_risk = cursor.fetchone()[0] * 5
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE type LIKE '%Distraction%'")
        dist_risk = cursor.fetchone()[0] * 15
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE type LIKE '%Inspection%'")
        insp_risk = cursor.fetchone()[0] * 10
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE type LIKE '%Guardian%'")
        guard_risk = cursor.fetchone()[0] * 12

        risk_data = [
            min(100, high_risk + 20),
            min(100, dist_risk + 10),
            min(100, insp_risk + 30),
            min(100, guard_risk + 10),
            min(100, med_risk + 15),
        ]

        # 3. Compliance Score (Base for Trend)
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE permit_status = 'Valid' AND training_status = 'Complete'")
        compliant_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        base_score = round((compliant_drivers / total_drivers) * 100, 1) if total_drivers else 94.0

        return {
            "success": True,
            "violation_breakdown": {
                "labels": violation_labels if violation_labels else ["No Data"],
                "data": violation_data if violation_data else [1],
            },
            "risk_matrix": {
                "data": risk_data
            },
            "compliance_base": base_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/{incident_id}/audit")
def get_incident_audit_log(incident_id: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incident_audit_log WHERE incident_id = ? ORDER BY timestamp ASC", (incident_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return {"success": True, "audit_log": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

