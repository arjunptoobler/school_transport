from .state import AgentState
from ..mcp.base import mcp_registry
from .llm import call_gemini


def compliance_agent(state: AgentState) -> dict:
    scenario = state["scenario"]

    # 1. Fetch live contexts
    drv = mcp_registry.call_tool("mcp_get_driver_record", driver_id="DRV-1045")
    name = drv.get("name", "Unknown Driver")
    permit = drv.get("permit_status", "Unknown")
    training = drv.get("training_status", "Unknown")

    res = mcp_registry.call_tool("mcp_lookup_policy", topic="guardian handover rules")
    if res:
        first_match = f"Rule match: {res[0]['text'][:200]}..."
    else:
        first_match = "No matching policy found."

    veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id="AU-BUS-104")
    mcp_registry.call_tool("mcp_update_inspection_status", vehicle_id="AU-BUS-104", status="failed")
    plate = veh.get("license_plate", "Unknown")

    # Set flow options
    if scenario == 0:
        fallback_msg = f"✅ Checked permit registry via PASS MCP. Driver {name} ({drv.get('driver_id')}) has permit status: {permit}. Training status: {training}."
        tool = "Driver Database, PASS MCP"
        next_step = "incident"
        prompt_desc = f"Checked PASS permit registry for driver {name} ({drv.get('driver_id')}). Permit is {permit}. Training: {training}."
    elif scenario == 1:
        fallback_msg = f"📚 RAG Query: 'guardian handover rules'. Result: {first_match}"
        tool = "Shared Policy RAG (ChromaDB)"
        next_step = "incident"
        prompt_desc = f"RAG search query returned compliance policies: {first_match}"
    elif scenario == 2:
        fallback_msg = f"❌ Pre-trip checklist failure: Bus AU-BUS-104 ({plate}) reported low brake pressure. Auto-grounding vehicle in Fleet MCP registry. Operating permit marked: Grounded."
        tool = "Fleet MCP, Pre-trip Forms"
        next_step = "incident"
        prompt_desc = f"Vehicle AU-BUS-104 failed brakes inspection. Registration: {plate}. Grounded."
    elif scenario == 3:
        from ..database.connection import get_db_connection

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
            pending_training = cursor.fetchone()[0]
        finally:
            conn.close()

        fallback_msg = f"✅ Querying violation and training logs. {pending_training} driver training renewals are currently pending or overdue."
        tool = "Driver MCP, Policy RAG"
        next_step = "incident"
        prompt_desc = f"Aggregated violation logs. Detected {pending_training} drivers pending training renewal certifications."
    else:
        fallback_msg = "✅ Compliance check completed. Records are valid."
        tool = "PASS MCP Lookup"
        next_step = "executive"
        prompt_desc = "All verification checks clean."

    # 2. Call LLM
    llm_msg = call_gemini(
        prompt=f"Formulate a regulatory compliance assessment. Context: {prompt_desc}. Make it formal and concise (1-2 sentences). Do not include greetings.",
        system_instruction="You are the Compliance Agent for the ADEK School Transportation Compliance Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Compliance Agent", "text": msg, "tool": tool}],
        "next_step": next_step,
    }
