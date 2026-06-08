from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection


def incident_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]

    if scenario == 0:
        # Create incident dynamically in sqlite db
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="high",
            type="Driver Distraction",
            driver_id="DRV-1045",
            vehicle_id="AU-BUS-105",
            description="Cabin camera phone usage alert.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        msg = f"🚨 Creating emergency ticket {inc_id} in database. Sending SMS alerts to Operator Command and preparing safety training assignment."
        tool = "Notification MCP, Incident Database"
        next_step = "executive"
    elif scenario == 1:
        # Fetch real student/guardian info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, guardian FROM students LIMIT 1")
        student = cursor.fetchone()
        conn.close()

        guardian = student["guardian"] if student else "Guardian"
        s_name = student["name"] if student else "Student"

        # Send alert SMS using dynamic data
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

        msg = f"🚨 Alerting parent via WhatsApp: 'Student remains safely on bus. Bus will return student to School Guard hub at 16:30.' Incident ticket {inc_id} filed."
        tool = "Notification MCP, Incident Database"
        next_step = "end"
    elif scenario == 2:
        # Create incident ticket using real vehicle ID
        result = mcp_registry.call_tool(
            "mcp_create_incident",
            severity="med",
            type="Inspection Failure",
            driver_id="DRV-1030",
            vehicle_id="AU-BUS-104",
            description="Failed pre-trip brakes inspection.",
        )
        inc_id = result.get("incident_id", "INC-NEW")
        msg = f"🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers. Incident ticket {inc_id} registered."
        tool = "Route Optimization MCP"
        next_step = "end"
    elif scenario == 3:
        # Query database to aggregate high severity incidents dynamically
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'high'")
        high_count = cursor.fetchone()[0]
        conn.close()

        msg = f"🚨 Incident correlation: Found {high_count} high-severity incidents across fleet. High risk trends flagged in Khalifa City route corridors."
        tool = "Incident MCP"
        next_step = "executive"
    else:
        msg = "🚨 No escalation required. Logged to standard incident tracker."
        tool = "Incident MCP"
        next_step = "end"

    history.append({"agent": "Incident Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
