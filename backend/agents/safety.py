from .state import AgentState
from ..mcp.base import mcp_registry
from ..database.connection import get_db_connection
from .llm import call_gemini


def safety_agent(state: AgentState) -> dict:
    scenario = state["scenario"]

    # 1. Fetch real contextual data from DB
    veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id="AU-BUS-105")
    plate = veh.get("license_plate", "Unknown Plate")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, route, guardian FROM students LIMIT 1")
        student = cursor.fetchone()
    finally:
        conn.close()

    s_name = student["name"] if student else "Student"
    route = student["route"] if student else "AU-Route-109"

    # Default fallback messages
    if scenario == 0:
        fallback_msg = f"⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 ({plate}) shows driver looking at phone for >4 seconds. Alert issued to driver console."
        tool = "Cabin Camera Edge Sensor, Incident MCP"
        next_step = "compliance"
        prompt_desc = f"Distraction alert: Cabin camera on Bus AU-BUS-105 ({plate}) detected phone usage. Console alert issued."
    elif scenario == 1:
        fallback_msg = f"⚠️ [Missing Guardian] Supervisor on {route} reports Grade 2 student {s_name} Guardian not present at stop #4."
        tool = "Route Supervisor SOP App"
        next_step = "compliance"
        prompt_desc = f"Missing guardian: Supervisor on {route} reports Grade 2 student {s_name} has no guardian present at drop-off."
    else:
        fallback_msg = "🛡️ Safety Agent completed query. Evaluating risk profile."
        tool = "Incident MCP Lookup"
        next_step = "incident"
        prompt_desc = "Standard risk query completed."

    # 2. Try LLM Generation
    llm_msg = call_gemini(
        prompt=f"Formulate a professional safety status report. DB Context: {prompt_desc}. Next step is compliance analysis. Keep it concise (1-2 sentences). Do not include any greeting or conversational filler.",
        system_instruction="You are the Safety Agent of the ADEK School Transportation Compliance Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Safety Agent", "text": msg, "tool": tool}],
        "next_step": next_step,
    }
