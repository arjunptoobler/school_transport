from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..agents.graph import run_agentic_flow

router = APIRouter(prefix="/agents", tags=["LangGraph Orchestrator"])

class ScenarioRun(BaseModel):
    scenario_id: int
    query: str = ""

@router.post("/run_scenario")
def run_scenario_endpoint(req: ScenarioRun):
    try:
        history = run_agentic_flow(req.scenario_id, req.query)
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
