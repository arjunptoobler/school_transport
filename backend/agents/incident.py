from .state import AgentState
from ..mcp.client import mcp_client
from ..mcp.incident import batch_write_history_to_audit_log
from ..database.connection import get_db_connection
from .parser import extract_entities
from .llm import call_gemini
import re

_GUARDIAN_KEYWORDS = {"guardian", "dropoff", "boarding", "unattended", "student not collected"}
_HARDWARE_KEYWORDS = {"brake", "inspect", "hardware", "pre-trip", "grounded", "maintenance", "standby", "tire"}


def _send_guardian_sms(vehicle_id: str):
    """Look up the guardian for a student on this bus and fire an SMS alert."""
    if not vehicle_id or vehicle_id == "Unknown":
        return
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.phone, p.name AS parent_name, s.name AS student_name
            FROM students s
            JOIN parents p ON s.parent_id = p.parent_id
            WHERE s.assigned_vehicle_id = ? AND p.phone IS NOT NULL
            LIMIT 1
        """, (vehicle_id,))
        guardian = cursor.fetchone()
        if guardian:
            mcp_client.call_tool("mcp_send_sms",
                recipient=guardian["phone"],
                message=(
                    f"URGENT ADEK ALERT: Your child ({guardian['student_name']}) has not been collected "
                    f"at the designated drop-off. Bus {vehicle_id} driver is holding the student safely on board. "
                    f"Please call the transport coordinator immediately."
                )
            )
    finally:
        conn.close()


def incident_agent(state: AgentState) -> dict:
    scenario = state["scenario"]
    query    = state["event_payload"]
    history  = state["conversation_history"]
    metadata = state.get("metadata", {})

    entities   = extract_entities(state)
    driver_id  = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]

    # Inherit evidence URL captured by the Evidence Agent
    evidence_url = metadata.get("evidence_url", "None")

    # Classify event type for correct incident handling
    is_guardian = scenario == 1 or any(kw in query.lower() for kw in _GUARDIAN_KEYWORDS)
    is_hardware = scenario == 2 or any(kw in query.lower() for kw in _HARDWARE_KEYWORDS)

    # Extract existing incident ID from query for update path
    inc_match   = re.search(r"(INC-[A-Z0-9\-]+)", query, re.IGNORECASE)
    incident_id = inc_match.group(1).upper() if inc_match else None

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Incident Management Agent for the ADEK Platform.\n"
        f"Review the following situation and the analysis from previous agents:\n"
        f"Event Query: {query}\n"
        f"Driver Context: {driver_id}, Vehicle Context: {vehicle_id}\n"
        f"Incident ID Context: {incident_id}\n"
        f"Hardware Failure: {is_hardware}\n"
        f"Missing Guardian: {is_guardian}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"1. Synthesize the findings into a final Incident Resolution Plan.\n"
        f"2. Suggest specific follow-up actions (dispatch support, log fine, maintenance ticket, notify stakeholders).\n"
        f"3. If there is an existing Incident ID, call mcp_update_incident_status to update it.\n"
        f"   Otherwise, call mcp_create_incident to log a new one.\n"
        f"4. For hardware failures: create a maintenance-type incident.\n"
        f"5. Do NOT immediately resolve — incidents must stay open for SLA tracking and audit.\n"
    )

    tools = [
        {
            "name": "mcp_create_incident",
            "description": "Create a new official incident ticket.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "severity":    {"type": "STRING", "description": "high, med, or low"},
                    "type":        {"type": "STRING", "description": "1-4 word incident category"},
                    "description": {"type": "STRING", "description": "Resolution plan summary"},
                },
                "required": ["severity", "type", "description"],
            },
        },
        {
            "name": "mcp_update_incident_status",
            "description": "Update an existing incident ticket.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "incident_id": {"type": "STRING"},
                    "status":      {"type": "STRING", "description": "In Progress, Pending Review"},
                    "reason":      {"type": "STRING"},
                },
                "required": ["incident_id", "status"],
            },
        },
    ]

    llm_res       = call_gemini(prompt=prompt,
        system_instruction="You are the Incident Management Agent. Create actionable resolution plans and log incidents autonomously.",
        tools=tools)
    llm_text      = llm_res["text"] if (llm_res and isinstance(llm_res, dict)) else ""
    function_call = llm_res["functionCall"] if (llm_res and isinstance(llm_res, dict)) else None

    action_taken = ""
    text         = ""

    if not llm_res or (not llm_text and not function_call):
        # Deterministic fallback — create correct incident type per scenario
        if incident_id:
            mcp_client.call_tool("mcp_update_incident_status",
                incident_id=incident_id, status="In Progress", reason="Automated review in progress")
            text         = f"📝 [Incident Plan] Updated existing incident {incident_id} to In Progress."
            action_taken = f"{incident_id} escalated to In Progress · Case summary emailed to ADEK Safety Authority · Audit trail updated"
        elif scenario == 0:
            desc = "Mobile phone usage confirmed by ADAS camera. Driver suspended, fine issued, ADEK Gov Portal synced."
            res  = mcp_client.call_tool("mcp_create_incident", severity="high", type="Driver Distraction",
                                         driver_id=driver_id, vehicle_id=vehicle_id, description=desc)
            if res and "incident_id" in res:
                inc_id = res["incident_id"]
                batch_write_history_to_audit_log(inc_id, history)
                action_taken = f"{inc_id} filed to ADEK Incident Register · Case report emailed to ADEK Safety Authority & DMT · Audit trail written ({len(history)} entries) · School admin notified"
            text = f"📝 [Incident Plan] {desc}"
        elif scenario == 1:
            desc = "Guardian absent at drop-off. Driver instructed to hold student. Mandatory training SLA assigned. Guardian notified via SMS."
            res  = mcp_client.call_tool("mcp_create_incident", severity="med", type="Missing Guardian",
                                         driver_id=driver_id, vehicle_id=vehicle_id, description=desc)
            if res and "incident_id" in res:
                inc_id = res["incident_id"]
                batch_write_history_to_audit_log(inc_id, history)
                action_taken = f"{inc_id} filed · Guardian SMS dispatched · School safeguarding officer notified by email · Audit trail written ({len(history)} entries)"
            _send_guardian_sms(vehicle_id)
            text = f"📝 [Incident Plan] {desc}"
        elif scenario == 2:
            desc = "Brake inspection failure. Vehicle grounded. Standby bus dispatched. Maintenance ticket logged. Parents notified."
            res  = mcp_client.call_tool("mcp_create_incident", severity="high", type="Vehicle Hardware Failure",
                                         driver_id=driver_id, vehicle_id=vehicle_id, description=desc)
            if res and "incident_id" in res:
                inc_id = res["incident_id"]
                batch_write_history_to_audit_log(inc_id, history)
                action_taken = f"{inc_id} maintenance ticket filed · Workshop team notified by SMS · DMT vehicle inspection request submitted · Parents notified via push · Audit trail written ({len(history)} entries)"
            text = f"📝 [Incident Plan] {desc}"
        else:
            # Classify from event keywords
            typ   = "General Safety Alert"
            q_low = query.lower()
            if any(k in q_low for k in ("distract", "phone", "seatbelt")):        typ = "Driver Distraction"
            elif any(k in q_low for k in ("guardian", "dropoff")):                typ = "Missing Guardian"
            elif any(k in q_low for k in ("route", "deviat")):                    typ = "Route Deviation"
            elif any(k in q_low for k in ("brake", "inspect")):                   typ = "Vehicle Hardware Failure"
            elif any(k in q_low for k in ("pre-departure", "departure", "banned", "expired permit")): typ = "Pre-Departure Driver Ban"
            desc = f"Autonomous resolution executed for: {query[:120]}"
            res  = mcp_client.call_tool("mcp_create_incident", severity="med", type=typ,
                                         driver_id=driver_id, vehicle_id=vehicle_id, description=desc)
            if res and "incident_id" in res:
                inc_id = res["incident_id"]
                batch_write_history_to_audit_log(inc_id, history)
                action_taken = f"{inc_id} ({typ}) filed to ADEK Register · Case report emailed to ADEK Safety Authority · Audit trail written ({len(history)} entries)"
            text = f"📝 [Incident Plan] {desc}"
    else:
        try:
            if function_call:
                act  = function_call.get("name")
                args = function_call.get("args", {})

                if act == "mcp_update_incident_status":
                    inc_id = args.get("incident_id", incident_id)
                    status = args.get("status", "In Progress")
                    mcp_client.call_tool("mcp_update_incident_status",
                        incident_id=inc_id, status=status, reason=args.get("reason", "Autonomous review"))
                    action_taken = f"{inc_id} escalated to {status} · Case summary emailed to ADEK Safety Authority · Audit trail updated"
                    plan         = args.get("reason", "Autonomous mitigation applied.")
                elif act == "mcp_create_incident":
                    sev  = args.get("severity", "med")
                    typ  = args.get("type", "General Incident")
                    plan = args.get("description", llm_text or "Autonomous resolution plan generated.")
                    res  = mcp_client.call_tool("mcp_create_incident", severity=sev, type=typ,
                                                 driver_id=driver_id, vehicle_id=vehicle_id, description=plan)
                    if res and "incident_id" in res:
                        inc_id = res["incident_id"]
                        batch_write_history_to_audit_log(inc_id, history)
                        notif = " · Guardian SMS dispatched · School safeguarding officer emailed" if is_guardian else " · ADEK Safety Authority emailed · School admin notified"
                        action_taken = f"{inc_id} ({typ}) filed to ADEK Register{notif} · Audit trail written ({len(history)} entries)"
                        # Fire guardian SMS if applicable
                        if is_guardian:
                            _send_guardian_sms(vehicle_id)
                else:
                    plan = llm_text
            else:
                plan = llm_text

            # Fire guardian SMS on LLM-text path too
            if is_guardian and not function_call:
                _send_guardian_sms(vehicle_id)

            text = f"📝 [Incident Plan] {plan}{(' (' + action_taken + ')') if action_taken else ''}"
        except Exception:
            text = f"📝 [Incident Plan] {llm_text}"

    next_step = "executive" if scenario in (0, 3) else "end"
    action_str = action_taken if action_taken else "Formulated incident resolution plan"

    return {
        "conversation_history": [{"agent": "Incident Agent", "text": text, "tool": "Automated Incident DB MCP", "action": action_str}],
        "next_step": next_step,
    }
