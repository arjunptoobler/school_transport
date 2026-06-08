from .state import AgentState

def executive_agent(state: AgentState) -> AgentState:
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
