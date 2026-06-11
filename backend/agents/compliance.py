from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini
from ..database.connection import get_db_connection
import re


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_prior_agent_context(history: list) -> dict:
    """Extract structured A2A signals from previous agents' conversation history."""
    safety_risk = None
    evidence_confidence = None

    for entry in history:
        agent = entry.get("agent", "")
        text = entry.get("text", "")

        if "Safety Agent" in agent:
            m = re.search(r"Safety Risk:\s*(High|Medium|Low)", text, re.IGNORECASE)
            if m:
                safety_risk = m.group(1).capitalize()

        if "Evidence Agent" in agent:
            m = re.search(r"Confidence[:\s]+([\d.]+)%?", text, re.IGNORECASE)
            if m:
                evidence_confidence = float(m.group(1))

    return {
        "safety_risk": safety_risk or "Unknown",
        "evidence_confidence": evidence_confidence,
    }


def _get_driver_history(driver_id: str) -> dict:
    """Query past incidents, fines, and active SLAs for a driver."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT type, COUNT(*) as cnt FROM incidents WHERE driver_id = ? GROUP BY type",
            (driver_id,),
        )
        breakdown = {r["type"]: r["cnt"] for r in cursor.fetchall()}
        total = sum(breakdown.values())

        cursor.execute("SELECT COUNT(*) FROM fines WHERE driver_id = ?", (driver_id,))
        fine_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT sla_id, deadline_date, status FROM compliance_sla WHERE driver_id = ? AND status = 'Pending'",
            (driver_id,),
        )
        active_slas = [dict(r) for r in cursor.fetchall()]

        return {
            "total_incidents": total,
            "incident_breakdown": breakdown,
            "fine_count": fine_count,
            "active_slas": active_slas,
            "is_repeat_offender": total >= 3,
        }
    finally:
        conn.close()


def _detect_violation_type(query: str, violation_matrix: dict) -> tuple:
    """Map free-text event to violation type, fine amount, and authority."""
    q = query.lower()
    if any(w in q for w in ["mobile", "phone", "distraction", "distract"]):
        vm = violation_matrix.get("driver_distraction", {})
        return "Driver Distraction", vm.get("fine_aed", 5000), "DMT"
    if any(w in q for w in ["speed", "speeding"]):
        vm = violation_matrix.get("speeding_school_zone", {})
        return "Speed Violation", vm.get("fine_aed", 3000), "DMT"
    if any(w in q for w in ["inspect", "brake", "maintenance"]):
        return "Pre-trip Inspection Failure", 2000, "DMT"
    if any(w in q for w in ["seatbelt", "seat belt"]):
        return "Seatbelt Violation", 1000, "ADEK"
    return "Policy Violation", 1000, "ADEK"


# ── Main agent ────────────────────────────────────────────────────────────────

def compliance_agent(state: AgentState) -> dict:
    query    = state["event_payload"]
    scenario = state["scenario"]
    history  = state.get("conversation_history", [])

    entities   = extract_entities(state)
    driver_id  = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]
    topic      = entities["topic"] or query

    # ── Phase 1: Collect all inputs ──────────────────────────────────────────

    # 1.1  Parse A2A signals — only look at the last 2 agent messages to keep
    #      context tight. Earlier messages are already summarised in history.
    recent_history = history[-2:] if len(history) > 2 else history
    prior = _parse_prior_agent_context(recent_history)
    safety_risk         = prior["safety_risk"]
    evidence_confidence = prior["evidence_confidence"]

    # Trim history string passed to LLM: last 2 entries only
    history_str = "\n".join(f"{h['agent']}: {h['text']}" for h in recent_history)

    # 1.2  SLA overdue check — filter to this driver only so we don't pass
    #      the full global escalation list into the prompt
    sla_check     = mcp_registry.call_tool("mcp_check_sla_compliance")
    overdue_slas  = sla_check.get("escalations", [])
    driver_overdue = any(s["driver_id"] == driver_id for s in overdue_slas) if driver_id else False

    # 1.3  Driver record (permit, medical, training, operator)
    driver_data = {}
    if driver_id and driver_id != "Unknown":
        drv = mcp_registry.call_tool("mcp_get_driver_record", driver_id=driver_id)
        if drv and "error" not in drv:
            driver_data = drv

    # 1.4  Driver incident history and fines (repeat-offender detection)
    drv_history = {}
    if driver_id and driver_id != "Unknown":
        drv_history = _get_driver_history(driver_id)

    # 1.5  Vehicle compliance status
    vehicle_data = {}
    if vehicle_id and vehicle_id != "Unknown":
        veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id=vehicle_id)
        if veh and "error" not in veh:
            vehicle_data = veh

    # 1.6  Violation matrix — correct fine amounts per violation category
    violation_matrix = mcp_registry.call_tool("mcp_get_violation_matrix")

    # 1.7  RAG policy lookup — build a specific question so the vector search
    #      returns relevant chunks, not generic policy intro text.
    violation_type, fine_amount, fine_authority = _detect_violation_type(query, violation_matrix)
    rag_query = f"{violation_type} regulation enforcement rule ADEK {topic}"
    rag_res = mcp_registry.call_tool("mcp_lookup_policy", topic=rag_query)
    policy_text = (
        "\n".join(f"- {r['text'][:200]}" for r in rag_res[:3])
        if rag_res else "No specific policy retrieved."
    )

    # 1.8  Pre-departure compliance check — deterministic pass/fail before LLM.
    #      Triggered by events describing a driver attempting to start a vehicle.
    action_taken = ""

    _pre_departure_keywords = [
        "start", "starting", "departure", "pre-departure", "pre departure",
        "ignition", "beginning shift", "begin route", "vehicle start", "vehicle check",
    ]
    is_pre_departure = any(w in query.lower() for w in _pre_departure_keywords)

    pre_departure_result = {}
    replacement_driver = None

    if is_pre_departure and driver_data and driver_id and driver_id != "Unknown":
        permit_ok   = driver_data.get("permit_status") == "Valid"
        medical_ok  = driver_data.get("medical_status") == "Passed"
        training_ok = driver_data.get("training_status") in ("Complete", "Completed")
        pre_departure_pass = permit_ok and medical_ok and training_ok

        if not pre_departure_pass:
            failures = []
            if not permit_ok:   failures.append(f"Permit={driver_data.get('permit_status', '?')}")
            if not medical_ok:  failures.append(f"Medical={driver_data.get('medical_status', '?')}")
            if not training_ok: failures.append(f"Training={driver_data.get('training_status', '?')}")

            # Suspend the non-compliant driver immediately
            mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Suspended")
            mcp_registry.call_tool("mcp_sync_permit_status_with_gov", driver_id=driver_id, new_status="Suspended")
            mcp_registry.call_tool("mcp_submit_adek_compliance_report",
                                   report_type="Violation", driver_id=driver_id, severity="HIGH",
                                   narrative=f"Pre-departure check failed: {', '.join(failures)}. Departure blocked.")

            # Find a replacement driver from same operator
            repl = mcp_registry.call_tool(
                "mcp_find_available_driver",
                exclude_driver_id=driver_id,
                operator=driver_data.get("operator"),
            )
            replacement_driver = repl if (repl and repl.get("found")) else None
            action_taken = (
                f"Pre-departure FAILED — banned {driver_id} ({', '.join(failures)})"
                + (f" | Replacement: {replacement_driver['name']} ({replacement_driver['driver_id']})"
                   if replacement_driver else " | No replacement available — route DELAYED")
            )
            pre_departure_result = {"passed": False, "failures": failures, "replacement": replacement_driver}
        else:
            pre_departure_result = {"passed": True, "failures": []}

    # ── Phase 2: Enriched LLM prompt ─────────────────────────────────────────

    # Pre-departure section injected into prompt when relevant
    if pre_departure_result:
        if pre_departure_result["passed"]:
            pre_dep_section = "=== PRE-DEPARTURE CHECK ===\nRESULT: APPROVED — Permit, Medical, Training all valid. Departure cleared.\n\n"
        else:
            repl_info = (
                f"Replacement assigned: {replacement_driver['name']} ({replacement_driver['driver_id']})"
                if replacement_driver else "No replacement driver available — route delayed."
            )
            pre_dep_section = (
                f"=== PRE-DEPARTURE CHECK ===\n"
                f"RESULT: REJECTED — {', '.join(pre_departure_result['failures'])}\n"
                f"Actions already taken: Driver banned, permit suspended, gov portal synced.\n"
                f"{repl_info}\n"
                f"NOTE: enforcement actions are complete. Write professional narrative only — do NOT change ACTION.\n\n"
            )
    else:
        pre_dep_section = ""

    prompt = (
        f"You are the Compliance Agent for the ADEK School Transport Platform.\n"
        f"Analyze the situation and enforce ADEK regulations autonomously.\n\n"
        f"=== EVENT ===\n"
        f"Query: {query}\n\n"
        f"{pre_dep_section}"
        f"=== PRIOR AGENT CONTEXT (A2A) ===\n"
        f"Safety Agent Risk Level: {safety_risk}\n"
        f"Evidence Confidence: {f'{evidence_confidence}%' if evidence_confidence else 'Not available'}\n"
        f"Conversation so far:\n{history_str}\n\n"
        f"=== DRIVER RECORD ===\n"
        f"Driver ID: {driver_data.get('driver_id', 'Unknown')}\n"
        f"Name: {driver_data.get('name', 'Unknown')}\n"
        f"Permit Status: {driver_data.get('permit_status', 'Unknown')}\n"
        f"Medical Status: {driver_data.get('medical_status', 'Unknown')}\n"
        f"Training Status: {driver_data.get('training_status', 'Unknown')}\n"
        f"Operator: {driver_data.get('operator', 'Unknown')}\n\n"
        f"=== DRIVER INCIDENT HISTORY ===\n"
        f"Total Past Incidents: {drv_history.get('total_incidents', 0)}\n"
        f"Breakdown by Type: {drv_history.get('incident_breakdown', {})}\n"
        f"Prior Fines Issued: {drv_history.get('fine_count', 0)}\n"
        f"Active Training SLAs: {len(drv_history.get('active_slas', []))}\n"
        f"Repeat Offender (3+ incidents): {drv_history.get('is_repeat_offender', False)}\n"
        f"Has Overdue Training SLA: {driver_overdue}\n\n"
        f"=== VEHICLE STATUS ===\n"
        f"Vehicle ID: {vehicle_data.get('vehicle_id', 'Unknown')}\n"
        f"Inspection Status: {vehicle_data.get('inspection_status', 'Unknown')}\n"
        f"GPS Status: {vehicle_data.get('gps_status', 'Unknown')}\n"
        f"Age (years): {vehicle_data.get('age', 'Unknown')}\n"
        f"Capacity / Occupancy: {vehicle_data.get('capacity', '?')} / {vehicle_data.get('current_occupancy', '?')}\n\n"
        f"=== VIOLATION MATRIX ===\n"
        f"{violation_matrix}\n\n"
        f"=== RELEVANT ADEK POLICY (RAG) ===\n"
        f"{policy_text}\n\n"
        f"=== DECISION RULES ===\n"
        f"- Pre-departure check failed → ACTION: SUSPEND (already executed — confirm in narrative).\n"
        f"- Pre-departure check passed → ACTION: NONE, narrative confirms departure approved.\n"
        f"- Repeat offender (3+ incidents) OR overdue SLA → SUSPEND.\n"
        f"- High safety risk + first offence + severe violation → SUSPEND.\n"
        f"- High safety risk + first offence + minor violation → ASSIGN_TRAINING.\n"
        f"- Low risk + first offence → ASSIGN_TRAINING or NONE.\n"
        f"- Vehicle inspection_status = 'failed' → GROUND_VEHICLE: YES.\n\n"
        f"=== TASK ===\n"
        f"1. Respond professionally citing the specific ADEK policy rule.\n"
        f"2. State the ACTION: SUSPEND, ASSIGN_TRAINING, or NONE.\n"
        f"3. State GROUND_VEHICLE: YES or NO.\n"
        f"4. State ROUTE: 'incident' (action taken) or 'executive' (audit only).\n\n"
        f"Output format exactly:\n"
        f"CHAT_RESPONSE: <your professional compliance assessment>\n"
        f"ACTION: <SUSPEND, ASSIGN_TRAINING, or NONE>\n"
        f"GROUND_VEHICLE: <YES or NO>\n"
        f"ROUTE: <incident or executive>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction=(
            "You are an expert Compliance Enforcement Agent for UAE ADEK transportation regulations. "
            "You calibrate decisions by safety risk level and repeat-offender history, and act autonomously."
        ),
    )

    # ── Parse LLM output or use fallback ─────────────────────────────────────

    # Scenarios where vehicle must be grounded regardless of LLM (inspection failure)
    fallback_ground = {2: True}

    if not llm_msg:
        repl_info = (
            f" Replacement: {replacement_driver['name']} ({replacement_driver['driver_id']})."
            if replacement_driver else " No replacement available — route delayed."
        ) if pre_departure_result and not pre_departure_result.get("passed") else ""

        fallbacks = {
            0: ("🤖 [Compliance] Mobile phone usage detected. ADEK Reg 4.2.1 violated. Escalating to Incident.", "SUSPEND", "incident"),
            1: ("🤖 [Compliance] Missing guardian at drop-off. ADEK Rule 7.3 violated. Training assigned.", "ASSIGN_TRAINING", "incident"),
            2: ("🤖 [Compliance] Pre-trip inspection failure. ADEK Fleet Rule 9.1 violated. Vehicle grounded.", "ASSIGN_TRAINING", "incident"),
            3: ("🤖 [Compliance] Weekly compliance audit complete. KPIs aggregated.", "NONE", "executive"),
            4: (f"🤖 [Compliance] Pre-departure check failed. Driver banned per ADEK Operator Reg 3.1.{repl_info}", "SUSPEND", "incident"),
        }
        text, act, next_step = fallbacks.get(
            scenario,
            ("🤖 [Compliance] Compliance status verified against RAG policy rules.", "NONE", "incident"),
        )
        ground_vehicle = fallback_ground.get(scenario, False) or (
            vehicle_data.get("inspection_status", "") == "failed"
        )

        # Skip driver actions if pre-departure already handled them
        if not action_taken:
            if act == "SUSPEND" and driver_id and driver_id != "Unknown":
                mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Suspended")
                mcp_registry.call_tool("mcp_sync_permit_status_with_gov", driver_id=driver_id, new_status="Suspended")
                mcp_registry.call_tool("mcp_submit_adek_compliance_report", report_type="Violation", driver_id=driver_id, severity="HIGH", narrative=f"Driver suspended. {violation_type}.")
                action_taken = f"Suspended {driver_id} & synced to ADEK Gov Portal"
            elif act == "ASSIGN_TRAINING" and driver_id and driver_id != "Unknown":
                mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Valid", training_status="Pending Refresher")
                mcp_registry.call_tool("mcp_submit_adek_compliance_report", report_type="Warning", driver_id=driver_id, severity="MEDIUM", narrative="Assigned remedial training.")
                action_taken = f"Assigned training to {driver_id} & notified ADEK"

        if ground_vehicle and vehicle_id and vehicle_id != "Unknown":
            mcp_registry.call_tool("mcp_update_inspection_status", vehicle_id=vehicle_id, status="grounded")
            action_taken = (f"{action_taken} | " if action_taken else "") + f"Grounded {vehicle_id} in DB"

    else:
        try:
            chat_m   = re.search(r"CHAT_RESPONSE:\s*(.*)", llm_msg, re.IGNORECASE | re.DOTALL)
            act_m    = re.search(r"ACTION:\s*(SUSPEND|ASSIGN_TRAINING|NONE)", llm_msg, re.IGNORECASE)
            route_m  = re.search(r"ROUTE:\s*(incident|executive)", llm_msg, re.IGNORECASE)
            ground_m = re.search(r"GROUND_VEHICLE:\s*(YES|NO)", llm_msg, re.IGNORECASE)

            raw_chat       = chat_m.group(1).split("ACTION:")[0].strip() if chat_m else llm_msg.strip()
            act            = act_m.group(1).strip().upper() if act_m else "NONE"
            next_step      = route_m.group(1).strip().lower() if route_m else "incident"
            next_step      = next_step if next_step in ("incident", "executive") else "incident"
            ground_vehicle = ground_m.group(1).strip().upper() == "YES" if ground_m else (
                vehicle_data.get("inspection_status", "") == "failed"
            )
            text = f"🤖 {raw_chat}"

            # Skip driver actions if pre-departure already handled them
            if not action_taken:
                if act == "SUSPEND" and driver_id and driver_id != "Unknown":
                    mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Suspended")
                    mcp_registry.call_tool("mcp_sync_permit_status_with_gov", driver_id=driver_id, new_status="Suspended")
                    mcp_registry.call_tool("mcp_submit_adek_compliance_report", report_type="Violation", driver_id=driver_id, severity="HIGH", narrative=f"Driver suspended. {violation_type}. Repeat offender: {drv_history.get('is_repeat_offender', False)}.")
                    action_taken = f"Suspended {driver_id} & synced with ADEK Gov Portal"
                elif act == "ASSIGN_TRAINING" and driver_id and driver_id != "Unknown":
                    mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Valid", training_status="Pending Refresher")
                    mcp_registry.call_tool("mcp_submit_adek_compliance_report", report_type="Warning", driver_id=driver_id, severity="MEDIUM", narrative="Assigned remedial training.")
                    action_taken = f"Assigned training to {driver_id} & notified ADEK"

            if ground_vehicle and vehicle_id and vehicle_id != "Unknown":
                mcp_registry.call_tool("mcp_update_inspection_status", vehicle_id=vehicle_id, status="grounded")
                action_taken = (f"{action_taken} | " if action_taken else "") + f"Grounded {vehicle_id} in DB"

        except Exception:
            text      = f"🤖 {llm_msg.strip()}"
            act       = "NONE"
            next_step = "incident"

    # ── Build output ──────────────────────────────────────────────────────────

    action_str = action_taken if action_taken else "Checked compliance registry, incident history & RAG policy"
    suffix     = f" (Action: {action_taken})" if action_taken else ""

    return {
        "conversation_history": [{
            "agent":  "Compliance Agent",
            "text":   f"{text}{suffix}",
            "tool":   "RAG + Incident History DB + Driver & Vehicle MCPs",
            "action": action_str,
        }],
        "next_step": next_step,
    }
