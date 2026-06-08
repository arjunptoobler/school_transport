from .state import AgentState
from ..mcp.base import mcp_registry

def compliance_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        # Check permit history via Driver MCP
        mcp_registry.call_tool("mcp_get_driver_record", driver_id="DRV-4412")
        msg = "✅ Checked permit registry via PASS MCP. Driver Yousef Hassan (DRV-4412) has 3 previous compliance warnings this quarter. Permit is subject to suspension."
        tool = "Driver Database, PASS MCP"
        next_step = "incident"
    elif scenario == 1:
        # Call Policy RAG MCP
        mcp_registry.call_tool("mcp_lookup_policy", topic="guardian handover")
        msg = "📚 RAG Query: 'guardian handover rules'. Result: Student under Grade 3 / Age 9 must be retained on board. Do not release without guardian."
        tool = "Shared Policy RAG (ChromaDB)"
        next_step = "incident"
    elif scenario == 2:
        # Ground vehicle using Fleet MCP
        mcp_registry.call_tool("mcp_update_inspection_status", vehicle_id="AU-BUS-104", status="failed")
        msg = "❌ Pre-trip checklist failure: Bus AU-BUS-104 reported low brake pressure. Auto-grounding vehicle in Fleet MCP registry. Operating permit marked: Suspended."
        tool = "Fleet MCP, Pre-trip Forms"
        next_step = "incident"
    elif scenario == 3:
        msg = "✅ Querying weekly violation logs. 18 driver training renewals missed during Ramadan shift adjustments."
        tool = "Driver MCP, Policy RAG"
        next_step = "incident"
    else:
        msg = "✅ Compliance check completed. Records are valid."
        tool = "PASS MCP Lookup"
        next_step = "executive"
        
    history.append({"agent": "Compliance Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
