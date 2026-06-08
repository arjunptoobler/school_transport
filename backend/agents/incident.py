from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection
from .llm import call_gemini


def incident_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]

    # Retrieve common database variables
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, guardian FROM students LIMIT 1")
    student = cursor.fetchone()
    conn.close()

    s_name = student["name"] if student else "Student"
    guardian = student["guardian"] if student else "Guardian"

    if scenario == 0:
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="high",
            type="Driver Distraction",
            driver_id="DRV-1045",
            vehicle_id="AU-BUS-105",
            description="Cabin camera phone usage alert.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        fallback_msg = f"🚨 Creating emergency ticket {inc_id} in database. Sending SMS alerts to Operator Command and preparing safety training assignment."
        tool = "Notification MCP, Incident Database"
        next_step = "executive"
        prompt_desc = f"Filing high-severity ticket {inc_id} for driver distraction (DRV-1045). Alerting command centre."
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
            driver_id="DRV-1024",
            vehicle_id="AU-BUS-102",
            description=f"Guardian {guardian} not present for student {s_name}.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        fallback_msg = f"🚨 Alerting parent via WhatsApp: 'Student remains safely on bus. Bus will return student to School Guard hub at 16:30.' Incident ticket {inc_id} filed."
        tool = "Notification MCP, Incident Database"
        next_step = "end"
        prompt_desc = f"Guardian {guardian} absent at stop. Student {s_name} held safely on board. Parent alerted via SMS/WhatsApp. Filed ticket {inc_id}."
    elif scenario == 2:
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="med",
            type="Inspection Failure",
            driver_id="DRV-1030",
            vehicle_id="AU-BUS-104",
            description="Failed pre-trip brakes inspection.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        fallback_msg = f"🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers. Incident ticket {inc_id} registered."
        tool = "Route Optimization MCP"
        next_step = "end"
        prompt_desc = f"Logged pre-trip checklist failure {inc_id} for AU-BUS-104. Recalculated dynamic route, standby bus AU-BUS-106 dispatched."
    elif scenario == 3:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'high'")
        high_count = cursor.fetchone()[0]
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
    history.append({"agent": "Incident Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
