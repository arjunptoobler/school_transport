from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection
from .parser import extract_entities
from .llm import call_gemini


def incident_agent(state: AgentState) -> dict:
    scenario = state["scenario"]

    # Extract dynamic parameters
    entities = extract_entities(state)
    driver_id = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]

    # Retrieve common database variables
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, guardian FROM students LIMIT 1")
        student = cursor.fetchone()
    finally:
        conn.close()

    s_name = student["name"] if student else "Student"
    guardian = student["guardian"] if student else "Guardian"

    if scenario == 0:
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="high",
            type="Driver Distraction",
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            description="Cabin camera phone usage alert.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Notification")
        fallback_msg = f"🚨 Creating emergency ticket {inc_id} in database. Sending SMS alerts to Operator Command and preparing safety training assignment."
        tool = "Notification MCP, Incident Database"
        next_step = "executive"
        prompt_desc = f"Filing high-severity ticket {inc_id} for driver distraction ({driver_id}) on bus {vehicle_id}. Alerting command centre. Lifecycle: Notification."
    elif scenario == 1:
        mcp_registry.call_tool(
            "mcp_send_sms",
            recipient="+971501234567",
            message=f"Alert: {s_name} remains safely on bus due to missing guardian. Bus returning to hub.",
        )
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="med",
            type="Missing Guardian",
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            description=f"Guardian {guardian} not present for student {s_name}.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Investigation")
        fallback_msg = f"🚨 Alerting parent via WhatsApp: 'Student remains safely on bus. Bus will return student to School Guard hub at 16:30.' Incident ticket {inc_id} filed."
        tool = "Notification MCP, Incident Database"
        next_step = "end"
        prompt_desc = f"Guardian {guardian} absent at stop. Student {s_name} held safely on board by driver {driver_id} on vehicle {vehicle_id}. Parent alerted via SMS/WhatsApp. Filed ticket {inc_id}. Lifecycle: Investigation."
    elif scenario == 2:
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="med",
            type="Inspection Failure",
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            description="Failed pre-trip brakes inspection.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        mcp_registry.call_tool("mcp_update_incident_status", incident_id=inc_id, status="Resolution")
        fallback_msg = f"🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers. Incident ticket {inc_id} registered."
        tool = "Route Optimization MCP"
        next_step = "end"
        prompt_desc = f"Logged pre-trip checklist failure {inc_id} for {vehicle_id} under driver {driver_id}. Recalculated dynamic route, standby bus AU-BUS-106 dispatched. Lifecycle: Resolution."
    elif scenario == 3:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'high'")
            high_count = cursor.fetchone()[0]
        finally:
            conn.close()

        fallback_msg = f"🚨 Incident correlation: Found {high_count} high-severity incidents across fleet. High risk trends flagged in Khalifa City route corridors."
        tool = "Incident MCP"
        next_step = "executive"
        prompt_desc = f"Analysed violation trends. Flagged correlation between {high_count} high-severity incidents and new routes in Khalifa City."
    else:
        fallback_msg = "🚨 No escalation required. Logged to standard incident tracker."
        tool = "Incident MCP"
        next_step = "end"
        prompt_desc = "Clean check. Logged to repository audit log."

    # Call LLM
    llm_msg = call_gemini(
        prompt=f"Formulate an incident log summary. Context: {prompt_desc}. Make it action-oriented and concise (1-2 sentences). Do not use conversational filler.",
        system_instruction="You are the Incident Management Agent for the ADEK School Transportation Compliance Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Incident Agent", "text": msg, "tool": tool}],
        "next_step": next_step,
    }
