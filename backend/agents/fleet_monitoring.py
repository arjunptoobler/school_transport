from .state import AgentState
from ..mcp.client import mcp_client
from .parser import extract_entities
from .llm import call_gemini
import re

_HARDWARE_KEYWORDS  = {"brake", "hydraulic", "pre-trip", "inspect", "mechanical", "sensor", "gps offline", "tire", "hardware", "failed", "grounded"}
_GUARDIAN_KEYWORDS  = {"guardian", "dropoff", "drop-off", "boarding", "unattended", "not collected"}


def fleet_monitoring_agent(state: AgentState) -> dict:
    """Agent for Real-Time School Transportation Monitoring (PRD 3.1).
    For hardware failures (Workflow 4) it grounds the vehicle and hands off
    to Route Optimization to dispatch a standby bus."""
    query    = state["event_payload"]
    scenario = state["scenario"]
    history  = state.get("conversation_history", [])

    entities   = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    veh = {}
    if vehicle_id and vehicle_id != "Unknown":
        res = mcp_client.call_tool("mcp_get_vehicle_status", vehicle_id=vehicle_id)
        if res and "error" not in res:
            veh = res

    # Workflow 3: missing guardian / boarding anomaly — routes directly to compliance
    is_guardian_path = scenario == 1 or any(kw in query.lower() for kw in _GUARDIAN_KEYWORDS)

    # Workflow 4: hardware / inspection failure path
    is_hardware_path = (
        scenario == 2
        or veh.get("inspection_status") == "failed"
        or veh.get("gps_status") == "offline"
        or any(kw in query.lower() for kw in _HARDWARE_KEYWORDS)
    )

    action_str      = "Evaluated GPS signal and passenger utilisation capacity"
    grounding_note  = ""

    if is_hardware_path and vehicle_id and vehicle_id != "Unknown":
        # Step 3 of Workflow 4 — ground the unsafe vehicle immediately
        mcp_client.call_tool("mcp_update_inspection_status", vehicle_id=vehicle_id, status="grounded")
        grounding_note = f"Grounded {vehicle_id} in fleet database"
        action_str     = f"Immediately grounded unsafe vehicle {vehicle_id} — routing for standby dispatch"

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Fleet Monitoring Agent for the ADEK Platform.\n"
        f"Analyze the following event for Real-Time School Transportation Monitoring:\n"
        f"Query/Event: {query}\n"
        f"Vehicle Context (GPS, Capacity, Occupancy): {veh}\n"
        f"Hardware Failure Detected: {is_hardware_path}\n"
        f"{'Vehicle has been grounded. Recommend standby bus dispatch and student transfer.' if is_hardware_path else ''}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"1. Evaluate GPS status, occupancy, and hardware state.\n"
        f"2. If hardware failure: vehicle is already grounded — recommend standby bus AU-BUS-106 dispatch.\n"
        f"3. If normal monitoring: suggest fleet operations actions.\n"
        f"Output format exactly:\n"
        f"ASSESSMENT: <your 1-2 sentence fleet status assessment>\n"
        f"ROUTE: <route_optimization or safety>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Fleet Operations Manager monitoring real-time GPS and student boarding telemetry.",
    )

    if not llm_msg:
        if is_hardware_path:
            text      = (
                f"📡 [Fleet Management] Vehicle {vehicle_id} grounded immediately — unsafe for operation. "
                f"Requesting standby bus AU-BUS-106 dispatch and student transfer route recalculation."
            )
            next_step = "route_optimization"
        elif is_guardian_path:
            text      = (
                f"📡 [Fleet Management] Vehicle {vehicle_id} manifest checked — guardian absent at designated stop. "
                f"Driver instructed to hold student on board. Routing to compliance for ADEK handover policy enforcement."
            )
            next_step = "compliance"
        else:
            text      = "📡 [Fleet Monitoring] GPS and capacity constraints evaluated. Routing for optimisation."
            next_step = "route_optimization"
    else:
        try:
            assessment = re.search(r"ASSESSMENT:\s*(.*)", llm_msg, re.IGNORECASE).group(1)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            if is_hardware_path:
                route_part = "route_optimization"
            elif is_guardian_path:
                route_part = "compliance"
            text = f"📡 [Fleet Analytics] {assessment}"
            if grounding_note:
                text += f" ({grounding_note})"
            next_step = route_part if route_part in ("route_optimization", "safety", "compliance") else (
                "route_optimization" if is_hardware_path else "compliance" if is_guardian_path else "safety"
            )
        except Exception:
            text      = f"📡 [Fleet Analytics] {llm_msg}"
            next_step = "route_optimization" if is_hardware_path else "compliance" if is_guardian_path else "safety"

    return {
        "conversation_history": [{"agent": "Fleet Monitoring Agent", "text": text, "tool": "Fleet GPS & Capacity MCP", "action": action_str}],
        "next_step": next_step,
    }
