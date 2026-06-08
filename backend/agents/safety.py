from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection


def safety_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]

    if scenario == 0:
        # Retrieve vehicle details dynamically from Fleet MCP
        veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id="AU-BUS-105")
        plate = veh.get("license_plate", "Unknown Plate")
        msg = f"⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 ({plate}) shows driver looking at phone for >4 seconds. Alert issued to driver console."
        tool = "Cabin Camera Edge Sensor, Incident MCP"
        next_step = "compliance"
    elif scenario == 1:
        # Retrieve a real student's route details dynamically from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, route, guardian FROM students LIMIT 1")
        student = cursor.fetchone()
        conn.close()

        if student:
            s_name = student["name"]
            route = student["route"]
            msg = f"⚠️ [Missing Guardian] Supervisor on {route} reports Grade 2 student {s_name} Guardian not present at stop #4."
        else:
            msg = "⚠️ [Missing Guardian] Supervisor reports Grade 2 student Guardian not present at drop-off."
        tool = "Route Supervisor SOP App"
        next_step = "compliance"
    else:
        msg = "🛡️ Safety Agent completed query. Evaluating risk profile."
        tool = "Incident MCP Lookup"
        next_step = "incident"

    history.append({"agent": "Safety Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
