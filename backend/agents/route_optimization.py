from .state import AgentState
from ..mcp.base import mcp_registry
import backend.mcp.route  # Import to register route tools
from .parser import extract_entities
from .llm import call_gemini
import re

def route_optimization_agent(state: AgentState) -> dict:
    """Agent specialized in Route Analytics and Optimization (PRD 3.6)."""
    query = state.get("event_payload", "") or ""
    scenario = state.get("scenario", -1)
    history = state.get("conversation_history", [])

    entities = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    # London Scenario roadblock detection
    roadblock_id = None
    if "block" in query.lower() or "closure" in query.lower() or "deviation" in query.lower() or scenario == 2:
        roadblock_id = "RB-LONDON-01"

    # Call the tool directly to compute route adjustments
    try:
        tool_fn = mcp_registry.get_tool("mcp_optimize_route")
        tool_res = tool_fn(vehicle_id=vehicle_id, roadblock_id=roadblock_id)
    except Exception as e:
        tool_res = {"error": f"Failed to execute solver: {str(e)}"}

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Route Optimization Agent for the ADEK Platform.\n"
        f"Analyze the following event for Route Analytics and Optimization:\n"
        f"Query/Event: {query}\n"
        f"Vehicle Target: {vehicle_id}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Routing Solver Tool Result:\n{tool_res}\n\n"
        f"Task:\n"
        f"1. Generate a recommendation describing the detour or dispatch changes using the Solver Tool results.\n"
        f"2. Incorporate the exact metrics from the Solver (distance in km, duration in minutes, standby bus ID if dispatched).\n"
        f"3. Determine if a detour is required (ACTION: EXECUTE_DETOUR or NONE) and the estimated delay in minutes (DELAY_MINS).\n"
        f"4. Decide the next routing step: 'compliance' (if policy check needed for detour) or 'executive' (if standard reporting).\n"
        f"Output format exactly:\n"
        f"RECOMMENDATION: <your 1-2 sentence route adjustment>\n"
        f"ACTION: <EXECUTE_DETOUR or NONE>\n"
        f"DELAY_MINS: <integer value of delay if detour, else 0>\n"
        f"ROUTE: <compliance or executive>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Route Optimizer, translating spatial solver outputs into clear human-friendly operational summaries.",
    )

    action_str = "Recalculated detour routes and bypassed delay zones"
    if not llm_msg:
        text = f"🔄 Route Optimization: Dynamic route recalibration completed. Adjusting schedule corridor."
        next_step = "compliance"
        if vehicle_id and vehicle_id != "Unknown":
            mcp_registry.call_tool("mcp_calculate_detour", vehicle_id=vehicle_id, obstacle_lat=24.45, obstacle_lng=54.37, radius_km=2.0)
            mcp_registry.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=8)
            mcp_registry.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=8, reason="Dynamic Detour")
            action_str = "Executed dynamic detour & propagated ETA updates"
    else:
        try:
            recommendation = re.search(r"RECOMMENDATION:\s*(.*)", llm_msg, re.IGNORECASE).group(1).split("ACTION:")[0]
            action_match = re.search(r"ACTION:\s*(.*)", llm_msg, re.IGNORECASE)
            delay_match = re.search(r"DELAY_MINS:\s*(\d+)", llm_msg, re.IGNORECASE)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            
            action_taken = ""
            if action_match and "EXECUTE_DETOUR" in action_match.group(1).upper() and vehicle_id and vehicle_id != "Unknown":
                delay = int(delay_match.group(1)) if delay_match else 5
                # Execute MCP Tools
                mcp_registry.call_tool("mcp_calculate_detour", vehicle_id=vehicle_id, obstacle_lat=24.45, obstacle_lng=54.37)
                mcp_registry.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=delay)
                mcp_registry.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=delay, reason="Safety/Traffic Detour")
                action_taken = f" (Action: Re-routed {vehicle_id}, broadcasted {delay}min ETA)"
                action_str = "Executed dynamic detour & propagated ETA updates"

            text = f"🔄 [Route Optimization] {recommendation.strip()}{action_taken}"
            next_step = route_part if route_part in ["compliance", "executive"] else "compliance"
        except Exception as e:
            text = f"🔄 [Route Optimization] {llm_msg}"
            next_step = "compliance"

    return {
        "conversation_history": [{"agent": "Route Optimization Agent", "text": text, "tool": "Route Optimizer Engine", "action": action_str}],
        "next_step": next_step
    }
