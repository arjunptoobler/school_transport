from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini

def route_optimization_agent(state: AgentState) -> dict:
    """Agent specialized in monitoring routing, GPS compliance, and capacity balancing."""
    scenario = state["scenario"]
    entities = extract_entities(state)
    vehicle_id = entities["vehicle_id"]
    driver_id = entities["driver_id"]

    fallback_msg = ""
    tool = "Route Optimizer Engine"
    next_step = "compliance"
    prompt_desc = ""

    # Check GPS or route deviation anomalies
    if scenario == 2: # Pre-trip fail
        fallback_msg = f"🔄 Route Optimization: Pre-trip grounding detected for Bus {vehicle_id}. Initiating fleet spare deployment to preserve schedule adherence."
        prompt_desc = f"Bus {vehicle_id} failed inspection. Coordinating spare vehicle swap to minimize delays."
        next_step = "compliance"
    elif "deviation" in state.get("user_query", "").lower() or "route" in state.get("user_query", "").lower():
        # Handle route deviation scenario
        fallback_msg = f"🔄 Route Optimization: GPS deviation warning on Bus {vehicle_id}. Analyzed detour due to school zone traffic. Adjusting schedule corridor by +8 mins."
        prompt_desc = f"Bus {vehicle_id} deviated from route. Detour analyzed. Rerouting via pre-approved sector."
        next_step = "compliance"
    else:
        # Generic capacity balance check
        fallback_msg = f"🔄 Route Optimization: Balancing passenger capacity on Route AU-44. Shifted 4 students to Bus {vehicle_id} to prevent overloading."
        prompt_desc = f"Checked school transit capacity. Balanced passenger allocations on route AU-44."
        next_step = "executive"

    llm_msg = call_gemini(
        prompt=f"Formulate a route optimization and scheduling recommendation. Context: {prompt_desc}. Keep it concise and professional (1-2 sentences). Do not include greetings.",
        system_instruction="You are the Route Optimization Agent for the ADEK School Transportation Safety Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Route Optimization Agent", "text": msg, "tool": tool}],
        "next_step": next_step
    }
