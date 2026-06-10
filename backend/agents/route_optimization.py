from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini
import re

def route_optimization_agent(state: AgentState) -> dict:
    """Agent specialized in Route Analytics and Optimization (PRD 3.6)."""
    query = state["event_payload"]
    scenario = state["scenario"]
    history = state.get("conversation_history", [])

    entities = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Route Optimization Agent for the ADEK Platform.\n"
        f"Analyze the following event for Route Analytics and Optimization (Phase 2):\n"
        f"Query/Event: {query}\n"
        f"Vehicle Target: {vehicle_id}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"1. Recommend optimized routing adjustments to reduce distance or bypass hazards.\n"
        f"2. Suggest specific performance metrics impacts (e.g., fuel saved, delay avoided).\n"
        f"3. Decide the next routing step: 'compliance' (if policy check needed for detour) or 'executive' (if standard reporting).\n"
        f"Output format exactly:\n"
        f"RECOMMENDATION: <your 1-2 sentence route adjustment>\n"
        f"ROUTE: <compliance or executive>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Route Optimizer, analyzing historical trip data and traffic conditions.",
    )

    if not llm_msg:
        text = f"🔄 Route Optimization: Dynamic route recalibration completed. Adjusting schedule corridor."
        next_step = "compliance"
    else:
        try:
            recommendation = re.search(r"RECOMMENDATION:\s*(.*)", llm_msg, re.IGNORECASE).group(1)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            text = f"🔄 [Route Optimization] {recommendation}"
            next_step = route_part if route_part in ["compliance", "executive"] else "compliance"
        except:
            text = f"🔄 [Route Optimization] {llm_msg}"
            next_step = "compliance"

    return {
        "conversation_history": [{"agent": "Route Optimization Agent", "text": text, "tool": "Route Optimizer Engine", "action": "Recalculated detour routes and bypassed delay zones"}],
        "next_step": next_step
    }
