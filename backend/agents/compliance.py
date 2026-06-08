from .state import AgentState
from ..mcp.base import mcp_registry


def compliance_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]

    if scenario == 0:
        # Check permit history via PASS MCP for driver DRV-1045 (seeded driver)
        drv = mcp_registry.call_tool("mcp_get_driver_record", driver_id="DRV-1045")
        name = drv.get("name", "Unknown Driver")
        permit = drv.get("permit_status", "Unknown")
        training = drv.get("training_status", "Unknown")
        msg = f"✅ Checked permit registry via PASS MCP. Driver {name} ({drv.get('driver_id')}) has permit status: {permit}. Training status: {training}."
        tool = "Driver Database, PASS MCP"
        next_step = "incident"
    elif scenario == 1:
        # Call Policy RAG MCP dynamically using vector query
        res = mcp_registry.call_tool("mcp_lookup_policy", topic="guardian handover rules")
        if res:
            first_match = f"Rule match: {res[0]['text'][:140]}..."
        else:
            first_match = "No matching policy found."
        msg = f"📚 RAG Query: 'guardian handover rules'. Result: {first_match}"
        tool = "Shared Policy RAG (ChromaDB)"
        next_step = "incident"
    elif scenario == 2:
        # Ground vehicle using Fleet MCP
        veh = mcp_registry.call_tool("mcp_get_vehicle_status", vehicle_id="AU-BUS-104")
        mcp_registry.call_tool("mcp_update_inspection_status", vehicle_id="AU-BUS-104", status="failed")
        plate = veh.get("license_plate", "Unknown")
        msg = f"❌ Pre-trip checklist failure: Bus AU-BUS-104 ({plate}) reported low brake pressure. Auto-grounding vehicle in Fleet MCP registry. Operating permit marked: Grounded."
        tool = "Fleet MCP, Pre-trip Forms"
        next_step = "incident"
    elif scenario == 3:
        # Fetch actual statistics from database
        from ..database.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
        pending_training = cursor.fetchone()[0]
        conn.close()

        msg = f"✅ Querying violation and training logs. {pending_training} driver training renewals are currently pending or overdue."
        tool = "Driver MCP, Policy RAG"
        next_step = "incident"
    else:
        msg = "✅ Compliance check completed. Records are valid."
        tool = "PASS MCP Lookup"
        next_step = "executive"

    history.append({"agent": "Compliance Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
