from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..agents.graph import run_agentic_flow

router = APIRouter(prefix="/agents", tags=["LangGraph Orchestrator"])

class ScenarioRun(BaseModel):
    scenario_id: int
    event_payload: str = ""
    event_timestamp: str = ""

@router.post("/run_scenario")
def run_scenario_endpoint(req: ScenarioRun):
    try:
        history = run_agentic_flow(req.scenario_id, req.event_payload, req.event_timestamp)
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
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
