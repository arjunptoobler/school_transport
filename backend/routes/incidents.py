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
            "INSERT INTO incidents VALUES (?,?,?,?,?,?,?)",
            (inc_id, req.severity, req.type, req.driver_id, req.vehicle_id, timestamp, req.description),
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
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
