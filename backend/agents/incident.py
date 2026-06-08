from .state import AgentState
from ..mcp.base import mcp_registry

def incident_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        # Create incident in sqlite db
        mcp_registry.call_tool("mcp_create_incident", 
                               severity="high", 
                               type="Driver Distraction", 
                               driver_id="DRV-4412", 
                               vehicle_id="AU-BUS-105", 
                               description="Cabin camera phone usage alert.")
        msg = "🚨 Creating emergency ticket INC-2026-882. Sending SMS alerts to Operator Command and preparing safety training assignment."
        tool = "Notification MCP, Incident Database"
        next_step = "executive"
    elif scenario == 1:
        # Parent contact notification and database logging
        mcp_registry.call_tool("mcp_send_sms", recipient="+971501234567", message="Student remains safely on bus. Bus will return to hub.")
        mcp_registry.call_tool("mcp_create_incident", 
                               severity="med", 
                               type="Missing Guardian", 
                               driver_id="DRV-1024", 
                               vehicle_id="AU-BUS-102", 
                               description="Guardian not present at drop-off.")
        msg = "🚨 Alerting parent via WhatsApp: 'Student remains safely on bus. Bus will return student to School Guard hub at 16:30.' Incident ticket INC-2026-881 filed."
        tool = "Notification MCP, Incident Database"
        next_step = "end"
    elif scenario == 2:
        mcp_registry.call_tool("mcp_create_incident", 
                               severity="med", 
                               type="Inspection Failure", 
                               driver_id="DRV-3041", 
                               vehicle_id="AU-BUS-104", 
                               description="Failed pre-trip brakes inspection.")
        msg = "🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers from Sheikha Fatima School."
        tool = "Route Optimization MCP"
        next_step = "end"
    elif scenario == 3:
        msg = "🚨 Incident correlation: High incident volumes matched with newer routes launched in Khalifa City."
        tool = "Incident MCP"
        next_step = "executive"
    else:
        msg = "🚨 No escalation required. Logged to standard incident tracker."
        tool = "Incident MCP"
        next_step = "end"
        
    history.append({"agent": "Incident Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}
