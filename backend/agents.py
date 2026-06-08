import os
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

# Import mock MCP tools
from .mcp_servers import (
    PolicyMCPServer,
    FleetMCPServer,
    DriverMCPServer,
    NotificationMCPServer,
    IncidentMCPServer
)

# Define LangGraph Agent State
class AgentState(TypedDict):
    scenario: int
    user_query: str
    current_agent: str
    conversation_history: List[Dict[str, str]]
    next_step: str
    metadata: Dict[str, Any]

# Specialized Agent Logic (orchestrated nodes)
def supervisor_node(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    query = state["user_query"]
    scenario = state["scenario"]
    
    msg = "🧠 Supervisor coordinated execution pipeline."
    history.append({"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router"})
    
    # Simple routing based on scenario or query
    if scenario == 0:
        next_step = "safety"
    elif scenario == 1:
        next_step = "safety"
    elif scenario == 2:
        next_step = "compliance"
    elif scenario == 3:
        next_step = "compliance"
    else:
        # Route query
        if "handover" in query.lower() or "guardian" in query.lower():
            next_step = "compliance"
        elif "phone" in query.lower() or "mobile" in query.lower() or "distraction" in query.lower():
            next_step = "safety"
        elif "inspection" in query.lower() or "brake" in query.lower():
            next_step = "compliance"
        else:
            next_step = "executive"
            
    return {**state, "conversation_history": history, "next_step": next_step}

def safety_node(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        msg = "⚠️ [Distraction Triggered] Cabin camera feed on Bus AU-BUS-105 shows driver looking at phone for >4 seconds. Alert issued to driver console."
        tool = "Cabin Camera Edge Sensor, Incident MCP"
        next_step = "compliance"
    elif scenario == 1:
        msg = "⚠️ [Missing Guardian] Supervisor on Route AU-102 reports Grade 2 student Guardian not present at stop #4."
        tool = "Route Supervisor SOP App"
        next_step = "compliance"
    else:
        msg = "🛡️ Safety Agent completed query. Evaluating risk profile."
        tool = "Incident MCP Lookup"
        next_step = "incident"
        
    history.append({"agent": "Safety Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": next_step}

def compliance_node(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        # Call Driver MCP tool
        rec = DriverMCPServer.get_driver_record("DRV-1045") # Mock record lookup
        msg = "✅ Checked permit registry via PASS MCP. Driver Yousef Hassan (DRV-4412) has 3 previous compliance warnings this quarter. Permit is subject to suspension."
        tool = "Driver Database, PASS MCP"
        next_step = "incident"
    elif scenario == 1:
        # Query Policy RAG
        rag_res = PolicyMCPServer.lookup_policy("guardian handover")
        msg = f"📚 RAG Query: 'guardian handover rules'. Result: Student under Grade 3 / Age 9 must be retained on board. Do not release without guardian."
        tool = "Shared Policy RAG (ChromaDB)"
        next_step = "incident"
    elif scenario == 2:
        # Pre-trip check failed
        msg = "❌ Pre-trip checklist failure: Bus AU-BUS-104 reported low brake pressure. Auto-grounding vehicle in Fleet MCP registry. Operating permit marked: Suspended."
        tool = "Fleet MCP, Pre-trip Forms"
        # Auto trigger repair
        FleetMCPServer.update_inspection_status("AU-BUS-104", "failed")
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

def incident_node(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        msg = "🚨 Creating emergency ticket INC-2026-882. Sending SMS alerts to Operator Command and preparing safety training assignment."
        tool = "Notification MCP, Incident Database"
        next_step = "executive"
        # Create mock incident in DB
        IncidentMCPServer.create_incident("INC-2026-882", "high", "Driver Distraction", "DRV-4412", "AU-BUS-105", "Cabin camera phone usage alert.")
    elif scenario == 1:
        msg = "🚨 Alerting parent via WhatsApp: 'Student remains safely on bus. Bus will return student to School Guard hub at 16:30.' Incident ticket INC-2026-881 filed."
        tool = "Notification MCP, Incident Database"
        next_step = "end"
        IncidentMCPServer.create_incident("INC-2026-881", "med", "Missing Guardian", "DRV-1024", "AU-BUS-102", "Guardian not present at drop-off.")
    elif scenario == 2:
        msg = "🗺️ Recalculated backup routing. Dispatching standby bus AU-BUS-106 to pick up passengers from Sheikha Fatima School."
        tool = "Route Optimization MCP"
        next_step = "end"
        IncidentMCPServer.create_incident("INC-2026-880", "med", "Inspection Failure", "DRV-3041", "AU-BUS-104", "Failed pre-trip brakes inspection.")
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

def executive_node(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]
    
    if scenario == 0:
        msg = "📊 Logged. Fleet safety score reduced to 94.2%. Recommending immediate driver stand-down."
        tool = "Analytics MCP"
    elif scenario == 3:
        msg = "📊 Synthesizing executive report. Compliance fell to 91% due to: 1. Training backlogs (60%), 2. Route delays in Khalifa City (40%). Recommending split shifts."
        tool = "Analytics MCP"
    else:
        msg = "📊 Executive report compiled. Safety indices are within target threshold."
        tool = "Analytics MCP"
        
    history.append({"agent": "Executive Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": "end"}

# Build LangGraph workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("safety", safety_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("incident", incident_node)
workflow.add_node("executive", executive_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Define conditional transitions
def route_next(state: AgentState):
    next_s = state["next_step"]
    if next_s == "end":
        return END
    return next_s

workflow.add_conditional_edges(
    "supervisor",
    route_next,
    {
        "safety": "safety",
        "compliance": "compliance",
        "incident": "incident",
        "executive": "executive",
        END: END
    }
)

workflow.add_conditional_edges("safety", route_next, {"compliance": "compliance", "incident": "incident", "executive": "executive", END: END})
workflow.add_conditional_edges("compliance", route_next, {"incident": "incident", "executive": "executive", END: END})
workflow.add_conditional_edges("incident", route_next, {"executive": "executive", END: END})
workflow.add_conditional_edges("executive", lambda x: END, {END: END})

# Compile agent graph
agent_graph = workflow.compile()

def run_agentic_flow(scenario_id: int, query: str = ""):
    initial_state = AgentState(
        scenario=scenario_id,
        user_query=query,
        current_agent="Supervisor Agent",
        conversation_history=[],
        next_step="supervisor",
        metadata={}
    )
    
    # Execute graph
    result = agent_graph.invoke(initial_state)
    return result["conversation_history"]

if __name__ == "__main__":
    print("Running test flow for Scenario 1...")
    history = run_agentic_flow(0)
    for h in history:
        print(f"[{h['agent']}]: {h['text']} ({h['tool']})")
