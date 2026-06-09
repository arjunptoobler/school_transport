from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini

def fleet_monitoring_agent(state: AgentState) -> dict:
    """Agent specialized in monitoring fleet health, GPS telemetry signals, and capacity utilization ratios."""
    scenario = state["scenario"]
    entities = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    fallback_msg = ""
    tool = "Fleet GPS Monitor & Telematics"
    next_step = "safety"
    prompt_desc = ""

    # Fetch vehicle record from MCP
    veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id=vehicle_id)
    plate = veh.get("license_plate", "Unknown")
    gps = veh.get("gps_status", "online")
    capacity = veh.get("capacity", 40)
    occupancy = veh.get("current_occupancy", 20)
    utilization = (occupancy / capacity) * 100 if capacity else 0

    if gps == "offline":
        fallback_msg = f"📡 Fleet Monitoring: Detected telemetry outage on Bus {vehicle_id} ({plate}). GPS signal is offline. Triggering automated fleet backup protocols."
        prompt_desc = f"Bus {vehicle_id} GPS telemetry signal is offline."
        next_step = "safety"
    elif utilization > 90.0:
        fallback_msg = f"📡 Fleet Monitoring: Critical capacity load on Bus {vehicle_id} ({plate}). Occupancy at {occupancy}/{capacity} ({utilization:.1f}% utilization). Exceeds safety guidelines."
        prompt_desc = f"Bus {vehicle_id} capacity load is high ({utilization:.1f}% utilization)."
        next_step = "safety"
    else:
        fallback_msg = f"📡 Fleet Monitoring: Bus {vehicle_id} ({plate}) is online. Active occupancy: {occupancy}/{capacity} ({utilization:.1f}% utilization). Route progression normal."
        prompt_desc = f"Bus {vehicle_id} is online and operational. Capacity load is {utilization:.1f}%."
        next_step = "executive"

    llm_msg = call_gemini(
        prompt=f"Formulate a fleet telemetry status report. Context: {prompt_desc}. Keep it concise and professional (1-2 sentences). Do not include greetings.",
        system_instruction="You are the Fleet Monitoring Agent for the ADEK School Transportation Safety Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Fleet Monitoring Agent", "text": msg, "tool": tool}],
        "next_step": next_step
    }
