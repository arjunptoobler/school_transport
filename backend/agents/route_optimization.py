from .state import AgentState
from ..mcp.client import mcp_client
from .parser import extract_entities
from .llm import call_gemini
import re

_HARDWARE_KEYWORDS = {"brake", "inspect", "standby", "hardware", "maintenance", "grounded", "pre-trip", "tire"}


def route_optimization_agent(state: AgentState) -> dict:
    """Agent for Route Analytics and Optimization (PRD 3.6).
    For hardware failures (Workflow 4) it dispatches a standby bus and pushes
    parent notifications, then routes to the Incident Agent for maintenance logging."""
    query    = state.get("event_payload", "") or ""
    scenario = state.get("scenario", -1)
    history  = state.get("conversation_history", [])

    entities   = extract_entities(state)
    vehicle_id = entities["vehicle_id"]

    # Workflow 4: hardware / maintenance path — must end at incident for maintenance ticket
    is_hardware_path = scenario == 2 or any(kw in query.lower() for kw in _HARDWARE_KEYWORDS)

    roadblock_id = None
    if any(kw in query.lower() for kw in ("block", "closure", "deviation")) or scenario == 2:
        roadblock_id = "RB-ADEK-01"

    tool_res = mcp_client.call_tool("mcp_optimize_route", vehicle_id=vehicle_id, roadblock_id=roadblock_id or "")

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Route Optimization Agent for the ADEK Platform.\n"
        f"Query/Event: {query}\n"
        f"Vehicle Target: {vehicle_id}\n"
        f"Hardware Failure Mode: {is_hardware_path}\n"
        f"Agent Context:\n{context_str}\n\n"
        f"Routing Solver Result:\n{tool_res}\n\n"
        f"Task:\n"
        f"1. Generate route recommendation using the Solver results.\n"
        f"2. If hardware failure: dispatch standby bus AU-BUS-106 and calculate merge route.\n"
        f"3. Include exact metrics (distance km, duration minutes, standby ID).\n"
        f"4. ACTION: EXECUTE_DETOUR (route blockage) or DISPATCH_STANDBY (hardware failure) or NONE.\n"
        f"5. ROUTE: 'incident' (hardware — for maintenance ticket) or 'compliance' (policy check) or 'executive' (reporting).\n"
        f"Output format exactly:\n"
        f"RECOMMENDATION: <1-2 sentence route adjustment>\n"
        f"ACTION: <EXECUTE_DETOUR or DISPATCH_STANDBY or NONE>\n"
        f"DELAY_MINS: <integer>\n"
        f"ROUTE: <incident or compliance or executive>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Route Optimizer for the ADEK school transport platform.",
    )

    action_str = "Recalculated detour routes and bypassed delay zones"

    if not llm_msg:
        if is_hardware_path:
            text      = (
                f"🔄 [Route Optimization] Standby bus AU-BUS-106 dispatched to cover {vehicle_id} route. "
                f"Merge route calculated. Parents notified of 12-minute delay via push notification."
            )
            next_step = "incident"
            if vehicle_id and vehicle_id != "Unknown":
                mcp_client.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=12)
                mcp_client.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=12, reason="Vehicle Grounded — Standby Dispatched")
                mcp_client.call_tool("mcp_send_push", recipient="parent_portal",
                    title="Bus Service Update",
                    message=f"Bus {vehicle_id} has been taken off service for safety. Standby bus AU-BUS-106 is en route. Expected delay: 12 minutes.")
            action_str = f"Standby AU-BUS-106 dispatched to {vehicle_id} route · Schedule updated +12 min · Push alert sent to parent portal · ETA broadcast to school admin · Route control notified by SMS"
        else:
            text      = "🔄 [Route Optimization] Dynamic route recalibration completed. Schedule adjusted."
            next_step = "compliance"
            if vehicle_id and vehicle_id != "Unknown":
                mcp_client.call_tool("mcp_calculate_detour", vehicle_id=vehicle_id, obstacle_lat=24.45, obstacle_lng=54.37, radius_km=2.0)
                mcp_client.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=8)
                mcp_client.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=8, reason="Dynamic Detour")
                mcp_client.call_tool("mcp_send_push", recipient="parent_portal",
                    title="Bus ETA Update",
                    message=f"Bus {vehicle_id} is delayed by 8 minutes due to a route adjustment.")
            action_str = f"Detour calculated for {vehicle_id} · Schedule updated +8 min · Push alert sent to parent portal · ETA broadcast to school admin & drivers"
    else:
        try:
            recommendation = re.search(r"RECOMMENDATION:\s*(.*)", llm_msg, re.IGNORECASE).group(1).split("ACTION:")[0]
            action_match   = re.search(r"ACTION:\s*(.*)", llm_msg, re.IGNORECASE)
            delay_match    = re.search(r"DELAY_MINS:\s*(\d+)", llm_msg, re.IGNORECASE)
            route_part     = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()

            act   = action_match.group(1).strip().upper() if action_match else "NONE"
            delay = int(delay_match.group(1)) if delay_match else (12 if is_hardware_path else 5)
            action_taken = ""

            if "DISPATCH_STANDBY" in act and vehicle_id and vehicle_id != "Unknown":
                mcp_client.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=delay)
                mcp_client.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=delay, reason="Standby Bus Dispatch")
                mcp_client.call_tool("mcp_send_push", recipient="parent_portal",
                    title="Bus Service Update",
                    message=f"Bus {vehicle_id} replaced by standby AU-BUS-106. Expected delay: {delay} minutes.")
                action_taken = f" (Action: Dispatched standby, pushed {delay}min delay to parent portal)"
                action_str   = f"Standby AU-BUS-106 dispatched · Schedule updated +{delay} min · Push alert sent to parent portal · ETA broadcast to school admin · Route control notified by SMS"
            elif "EXECUTE_DETOUR" in act and vehicle_id and vehicle_id != "Unknown":
                mcp_client.call_tool("mcp_calculate_detour", vehicle_id=vehicle_id, obstacle_lat=24.45, obstacle_lng=54.37)
                mcp_client.call_tool("mcp_update_bus_schedule", vehicle_id=vehicle_id, delay_minutes=delay)
                mcp_client.call_tool("mcp_broadcast_eta_change", vehicle_id=vehicle_id, delay_minutes=delay, reason="Safety/Traffic Detour")
                mcp_client.call_tool("mcp_send_push", recipient="parent_portal",
                    title="Bus ETA Update",
                    message=f"Bus {vehicle_id} delayed by {delay} minutes due to route adjustment.")
                action_taken = f" (Action: Re-routed {vehicle_id}, pushed {delay}min ETA to parent portal)"
                action_str   = f"Detour calculated for {vehicle_id} · Schedule updated +{delay} min · Push alert sent to parent portal · ETA broadcast to school admin & drivers"

            text = f"🔄 [Route Optimization] {recommendation.strip()}{action_taken}"
            if is_hardware_path and route_part != "incident":
                route_part = "incident"
            next_step = route_part if route_part in ("incident", "compliance", "executive") else (
                "incident" if is_hardware_path else "compliance"
            )
        except Exception:
            text      = f"🔄 [Route Optimization] {llm_msg}"
            next_step = "incident" if is_hardware_path else "compliance"

    return {
        "conversation_history": [{"agent": "Route Optimization Agent", "text": text, "tool": "Route Optimizer Engine", "action": action_str}],
        "next_step": next_step,
    }
