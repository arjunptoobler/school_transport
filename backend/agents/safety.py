from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection
from .parser import extract_entities
from .llm import call_gemini
import re

def safety_agent(state: AgentState) -> dict:
    query = state["event_payload"]
    scenario = state["scenario"]

    # Extract dynamic parameters
    entities = extract_entities(state)
    driver_id = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]

    # Fetch vehicle details dynamically from Fleet MCP
    veh = {}
    if vehicle_id and vehicle_id != "Unknown":
        veh_res = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id=vehicle_id)
        if veh_res and "error" not in veh_res:
            veh = veh_res

    # Try to find associated student info if mentioned
    student = None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, route, guardian FROM students LIMIT 1") # Mock matching for demo MVP
        student = dict(cursor.fetchone())
    finally:
        conn.close()

    prompt = (
        f"You are the Safety Agent for the ADEK Platform.\n"
        f"Analyze the following event/query for immediate physical safety risks to students or vehicles.\n"
        f"Event: {query}\n"
        f"Vehicle Context: {veh}\n"
        f"Student Context: {student}\n\n"
        f"Task:\n"
        f"1. Assess the immediate safety risk level (High, Medium, Low).\n"
        f"2. Suggest an immediate safety action (e.g., stop the bus, contact guardian, ignore if safe).\n"
        f"3. Decide the next routing step: 'evidence' (if telemetry/video needs reviewing), 'compliance' (if it's a policy issue), or 'incident' (if a major emergency).\n"
        f"Output format exactly:\n"
        f"RISK: <High/Medium/Low>\n"
        f"ASSESSMENT: <your 1-2 sentence safety assessment>\n"
        f"ROUTE: <evidence, compliance, or incident>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert Transportation Safety Officer. You prioritize student physical safety above all.",
    )

    if not llm_msg:
        if scenario == 0:
            text = "🛡️ [Safety Risk: High] Detected unsafe driver distraction (mobile usage). Immediate risk to passengers. Route to evidence to verify camera footage."
            next_step = "evidence"
        elif scenario == 1:
            text = "🛡️ [Safety Risk: Medium] Missing guardian at drop-off. Protocol initiated: student retained on board. Routing to compliance for protocol verification."
            next_step = "compliance"
        else:
            text = "🛡️ Safety risk query completed. Routing to compliance for policy check."
            next_step = "compliance"
    else:
        try:
            risk = re.search(r"RISK:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip()
            assessment = re.search(r"ASSESSMENT:\s*(.*)", llm_msg, re.IGNORECASE).group(1)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            text = f"🛡️ [Safety Risk: {risk}] {assessment}"
            next_step = route_part if route_part in ["evidence", "compliance", "incident"] else "compliance"
        except:
            text = f"🛡️ [Safety Analysis] {llm_msg}"
            next_step = "evidence"

    return {
        "conversation_history": [{"agent": "Safety Agent", "text": text, "tool": "Safety Rules & Incident DB", "action": f"Classified risk level and requested safety check."}],
        "next_step": next_step,
    }
