from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

from .database import DB_PATH
from .agents import run_agentic_flow
from .rag import query_policy

app = FastAPI(title="ADEK School Transportation AI Compliance Platform API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScenarioRequest(BaseModel):
    scenario_id: int
    query: str = ""

class RAGRequest(BaseModel):
    query: str

class IncidentRequest(BaseModel):
    severity: str
    type: str
    driver_id: str
    vehicle_id: str
    description: str

@app.get("/api/health")
def health():
    return {"status": "healthy"}

@app.post("/api/run_scenario")
def run_scenario(req: ScenarioRequest):
    try:
        history = run_agentic_flow(req.scenario_id, req.query)
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query_policy")
def query_policy_endpoint(req: RAGRequest):
    try:
        results = query_policy(req.query)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents")
def get_incidents():
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate_incident")
def simulate_incident(req: IncidentRequest):
    try:
        import datetime
        import random
        inc_id = f"INC-2026-{random.randint(1000, 9999)}"
        timestamp = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?,?)", 
                       (inc_id, req.severity, req.type, req.driver_id, req.vehicle_id, timestamp, req.description))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "incident": {
                "incident_id": inc_id,
                "severity": req.severity,
                "type": req.type,
                "driver_id": req.driver_id,
                "vehicle_id": req.vehicle_id,
                "timestamp": timestamp,
                "description": req.description
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fleet_status")
def get_fleet_status():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Drivers
        cursor.execute("SELECT * FROM drivers LIMIT 20")
        drivers = [
            {
                "driver_id": r[0],
                "name": r[1],
                "permit_status": r[2],
                "medical_status": r[3],
                "training_status": r[4],
                "operator": r[5]
            } for r in cursor.fetchall()
        ]
        
        # Vehicles
        cursor.execute("SELECT * FROM vehicles LIMIT 20")
        vehicles = [
            {
                "vehicle_id": r[0],
                "license_plate": r[1],
                "age": r[2],
                "gps_status": r[3],
                "inspection_status": r[4]
            } for r in cursor.fetchall()
        ]
        
        # Summary counts
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE permit_status = 'Valid'")
        valid_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE inspection_status = 'valid'")
        valid_vehicles = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        
        conn.close()
        return {
            "success": True,
            "drivers": drivers,
            "vehicles": vehicles,
            "summary": {
                "valid_drivers": valid_drivers,
                "total_drivers": total_drivers,
                "valid_vehicles": valid_vehicles,
                "total_vehicles": total_vehicles
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
