from .state import AgentState
from .llm import call_gemini


def supervisor_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    query = state["user_query"]
    scenario = state["scenario"]

    # Basic routing logic fallback
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

    # Dynamic LLM execution
    llm_msg = call_gemini(
        prompt=f"A user requested scenario {scenario} with query '{query}'. Act as the Supervisor and output a 1-sentence message coordinating this pipeline. Next agent is '{next_step}'. Keep it professional.",
        system_instruction="You are the Supervisor Agent for the ADEK School Transportation AI Compliance Platform.",
    )

    msg = llm_msg or "🧠 Supervisor coordinated execution pipeline."
    history.append({"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router"})

    return {**state, "conversation_history": history, "next_step": next_step}
