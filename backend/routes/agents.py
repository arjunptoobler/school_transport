from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..agents.graph import run_agentic_flow
from typing import List, Dict, Any
import time

router = APIRouter(prefix="/agents", tags=["LangGraph Orchestrator"])

class ScenarioRun(BaseModel):
    scenario_id: int
    event_payload: str = ""
    event_timestamp: str = ""

# In-memory store for recent agent flow runs (persists during backend lifetime)
RECENT_RUNS: List[Dict[str, Any]] = []

@router.get("/recent_runs")
def get_recent_runs():
    """Returns the list of recent agent flow executions."""
    return {"success": True, "runs": RECENT_RUNS}

@router.post("/run_scenario")
def run_scenario_endpoint(req: ScenarioRun):
    try:
        history = run_agentic_flow(req.scenario_id, req.event_payload, req.event_timestamp)
        
        # Save run entry
        run_entry = {
            "run_id": f"RUN-{int(time.time() * 1000)}",
            "scenario_id": req.scenario_id,
            "event_payload": req.event_payload,
            "timestamp": req.event_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "history": history
        }
        RECENT_RUNS.append(run_entry)
        if len(RECENT_RUNS) > 20:
            RECENT_RUNS.pop(0)
            
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/supervisor/event")
def supervisor_event_endpoint(req: ScenarioRun):
    """
    API endpoint designed specifically for external management systems to 
    inject incident events and webhooks into the Supervisor Agent.
    """
    try:
        history = run_agentic_flow(req.scenario_id, req.event_payload, req.event_timestamp)
        
        # Save run entry
        run_entry = {
            "run_id": f"RUN-{int(time.time() * 1000)}",
            "scenario_id": req.scenario_id,
            "event_payload": req.event_payload,
            "timestamp": req.event_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "history": history
        }
        RECENT_RUNS.append(run_entry)
        if len(RECENT_RUNS) > 20:
            RECENT_RUNS.pop(0)
            
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
