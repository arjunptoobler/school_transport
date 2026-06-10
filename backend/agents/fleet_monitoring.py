from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini
import re

def fleet_monitoring_agent(state: AgentState) -> dict:
    """Agent specialized in Real-Time School Transportation Monitoring (PRD 3.1)."""
    query = state["event_payload"]
    scenario = state["scenario"]
    history = state.get("conversation_history", [])

    entities = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    # Fetch vehicle record from MCP
    veh = {}
    if vehicle_id and vehicle_id != "Unknown":
        res = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id=vehicle_id)
        if res and "error" not in res:
            veh = res

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Fleet Monitoring Agent for the ADEK Platform.\n"
        f"Analyze the following event for Real-Time School Transportation Monitoring:\n"
        f"Query/Event: {query}\n"
        f"Vehicle Context (GPS, Capacity, Occupancy): {veh}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"1. Evaluate the GPS signal status and vehicle occupancy/capacity.\n"
        f"2. Suggest immediate fleet operations actions (e.g., alert dispatch, approve boarding, reroute).\n"
        f"3. Decide the next routing step: 'route_optimization' (if a reroute or spare is needed) or 'safety' (if overload/offline is critical).\n"
        f"Output format exactly:\n"
        f"ASSESSMENT: <your 1-2 sentence fleet status assessment>\n"
        f"ROUTE: <route_optimization or safety>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Fleet Operations Manager monitoring real-time GPS and student boarding telemetry.",
    )

    if not llm_msg:
        text = f"📡 Fleet Monitoring: GPS and capacity constraints evaluated. Moving to route optimization."
        next_step = "route_optimization"
    else:
        try:
            assessment = re.search(r"ASSESSMENT:\s*(.*)", llm_msg, re.IGNORECASE).group(1)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            text = f"📡 [Fleet Analytics] {assessment}"
            next_step = route_part if route_part in ["route_optimization", "safety"] else "safety"
        except:
            text = f"📡 [Fleet Analytics] {llm_msg}"
            next_step = "safety"

    return {
        "conversation_history": [{"agent": "Fleet Monitoring Agent", "text": text, "tool": "Fleet GPS & Capacity MCP", "action": "Evaluated GPS signal and passenger utilization capacity"}],
        "next_step": next_step
    }
