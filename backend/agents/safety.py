from .state import AgentState

def safety_agent(state: AgentState) -> AgentState:
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
