from .state import AgentState

def supervisor_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    query = state["user_query"]
    scenario = state["scenario"]
    
    msg = "🧠 Supervisor coordinated execution pipeline."
    history.append({"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router"})
    
    if scenario == 0:
        next_step = "safety"
    elif scenario == 1:
        next_step = "safety"
    elif scenario == 2:
        next_step = "compliance"
    elif scenario == 3:
        next_step = "compliance"
    else:
        # User query classification routing
        if any(w in query.lower() for w in ["handover", "guardian", "policy"]):
            next_step = "compliance"
        elif any(w in query.lower() for w in ["phone", "mobile", "distraction", "speed"]):
            next_step = "safety"
        else:
            next_step = "executive"
            
    return {**state, "conversation_history": history, "next_step": next_step}
