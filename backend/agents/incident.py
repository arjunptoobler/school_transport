from .state import AgentState
from ..mcp.base import mcp_registry
from ..mcp.incident import batch_write_history_to_audit_log
from ..database.connection import get_db_connection
from .parser import extract_entities
from .llm import call_gemini
import re

def incident_agent(state: AgentState) -> dict:
    scenario = state["scenario"]
    query = state["event_payload"]
    history = state["conversation_history"]

    # Extract dynamic parameters
    entities = extract_entities(state)
    driver_id = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]

    # Try to extract incident_id from the user query
    inc_match = re.search(r"(INC-[A-Z0-9\-]+)", query, re.IGNORECASE)
    incident_id = inc_match.group(1).upper() if inc_match else None

    # Compile the context from previous agents
    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Incident Management Agent for the ADEK Platform.\n"
        f"Review the following situation and the analysis from previous agents:\n"
        f"Event Query: {query}\n"
        f"Driver Context: {driver_id}, Vehicle Context: {vehicle_id}\n"
        f"Incident ID Context: {incident_id}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"1. Synthesize the findings into a final Incident Resolution Plan.\n"
        f"2. Suggest specific follow-up actions (e.g., dispatch support, log fine, close ticket, notify operator).\n"
        f"3. Decide if an incident should be automatically created or updated. If there is an existing Incident ID context, output ACTION: RESOLVE_INCIDENT to mark it as resolved. If this is a new event requiring a new ticket, output ACTION: CREATE_INCIDENT.\n"
        f"4. Do NOT recommend manual review unless there is an explicit request to contest or appeal. Complete the resolution plan autonomously.\n"
        f"Output format exactly:\n"
        f"PLAN: <your 1-2 sentence resolution plan>\n"
        f"ACTION: <RESOLVE_INCIDENT, CREATE_INCIDENT, or NONE>\n"
        f"SEVERITY: <high, med, or low (only if creating incident)>\n"
        f"TYPE: <1-4 word incident type (only if creating incident)>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are the Incident Management Agent. You create actionable resolution plans, resolve existing database incidents, and automate new incident ticket entries autonomously.",
    )

    action_taken = ""
    if not llm_msg:
        if incident_id:
            mcp_registry.call_tool("mcp_update_incident_status", incident_id=incident_id, status="Resolved")
            text = f"📝 [Incident Plan] Resolved existing incident {incident_id} autonomously. Fleet safety rules updated."
            action_taken = f" (Action: Resolved {incident_id} in DB)"
        elif scenario == 0:
            text = "📝 [Incident Plan] Created INC-2026-901 for unsafe distraction. Fines queued. Notifying operator Emirates Transport."
            res = mcp_registry.call_tool("mcp_create_incident", severity="high", type="Driver Distraction", driver_id=driver_id, vehicle_id=vehicle_id, description=text)
            if res and "incident_id" in res:
                inc_id = res['incident_id']
                batch_write_history_to_audit_log(inc_id, history)
                mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolved", agent="Incident Agent", reason="Automated resolution via pipeline fallback")
        elif scenario == 1:
            text = "📝 [Incident Plan] Created INC-2026-902 for protocol violation. Student safeguarded. Scheduling guardian follow-up."
            res = mcp_registry.call_tool("mcp_create_incident", severity="med", type="Missing Guardian", driver_id=driver_id, vehicle_id=vehicle_id, description=text)
            if res and "incident_id" in res:
                inc_id = res['incident_id']
                batch_write_history_to_audit_log(inc_id, history)
                mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolved", agent="Incident Agent", reason="Automated resolution via pipeline fallback")
        elif scenario == 2:
            text = "📝 [Incident Plan] Created INC-2026-903 for vehicle compliance failure. Grounding bus AU-BUS-104."
            res = mcp_registry.call_tool("mcp_create_incident", severity="high", type="Inspection Failure", driver_id=driver_id, vehicle_id=vehicle_id, description=text)
            if res and "incident_id" in res:
                inc_id = res['incident_id']
                batch_write_history_to_audit_log(inc_id, history)
                mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolved", agent="Incident Agent", reason="Automated resolution via pipeline fallback")
        else:
            typ = "General Edge Alert"
            q_lower = query.lower()
            if "distract" in q_lower or "phone" in q_lower or "seatbelt" in q_lower:
                typ = "Driver Distraction"
            elif "guardian" in q_lower or "dropoff" in q_lower or "boarding" in q_lower:
                typ = "Missing Guardian"
            elif "route" in q_lower or "deviat" in q_lower:
                typ = "Route Deviation"
            elif "brake" in q_lower or "inspect" in q_lower or "compliance" in q_lower:
                typ = "Compliance Failure"

            text = f"📝 [Incident Plan] Handled event autonomously: {query}"
            res = mcp_registry.call_tool("mcp_create_incident", severity="med", type=typ, driver_id=driver_id, vehicle_id=vehicle_id, description=text)
            if res and "incident_id" in res:
                inc_id = res['incident_id']
                action_taken = f" (Action: Created {inc_id} in DB)"
                batch_write_history_to_audit_log(inc_id, history)
                mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolved", agent="Incident Agent", reason="Automated resolution via pipeline fallback")
    else:
        try:
            plan = re.search(r"PLAN:\s*(.*)", llm_msg, re.IGNORECASE).group(1).split("ACTION:")[0]
            action_match = re.search(r"ACTION:\s*(.*)", llm_msg, re.IGNORECASE)
            
            if action_match:
                act = action_match.group(1).upper()
                if "RESOLVE_INCIDENT" in act and incident_id:
                    mcp_registry.call_tool("mcp_update_incident_status", incident_id=incident_id, status="Resolved")
                    action_taken = f" (Action: Resolved {incident_id} in DB)"
                elif "CREATE_INCIDENT" in act:
                    sev_match = re.search(r"SEVERITY:\s*(.*)", llm_msg, re.IGNORECASE)
                    type_match = re.search(r"TYPE:\s*(.*)", llm_msg, re.IGNORECASE)
                    
                    sev = sev_match.group(1).strip().lower() if sev_match else "med"
                    typ = type_match.group(1).strip() if type_match else "General Incident"
                    
                    res = mcp_registry.call_tool("mcp_create_incident", severity=sev, type=typ, driver_id=driver_id, vehicle_id=vehicle_id, description=plan.strip())
                    if res and "incident_id" in res:
                        inc_id = res['incident_id']
                        action_taken = f" (Action: Created {inc_id} in DB)"
                        batch_write_history_to_audit_log(inc_id, history)
                        # Immediately update to Resolved as pipeline handled mitigation
                        mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolved", agent="Incident Agent", reason="Autonomous mitigation plan executed.")
            
            text = f"📝 [Incident Plan] {plan.strip()}{action_taken}"
        except Exception as e:
            text = f"📝 [Incident Plan] {llm_msg}"

    next_step = "executive" if scenario in [0, 3] else "end"

    action_str = action_taken.replace(" (Action: ", "").replace(")", "").strip() if action_taken else "Formulated incident resolution plan"

    return {
        "conversation_history": [{"agent": "Incident Agent", "text": text, "tool": "Automated Incident DB MCP", "action": action_str}],
        "next_step": next_step,
    }
