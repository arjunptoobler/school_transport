from .state import AgentState
from .llm import call_gemini


def supervisor_agent(state: AgentState) -> dict:
    query = state["user_query"]
    scenario = state["scenario"]

    # Basic routing logic fallback
    if scenario == 0:
        next_step = "safety"
    elif scenario == 1:
        next_step = "safety"
    elif scenario == 2:
        next_step = "route_optimization"
    elif scenario == 3:
        next_step = "compliance"
    else:
        # LLM Autonomous routing classification
        routing_prompt = (
            f"Classify the following query: '{query}'.\n"
            f"Return exactly one word matching the next agent name:\n"
            f"- 'safety': for distractions, cameras, speed violations, missing guardian, or physical route safety issues.\n"
            f"- 'compliance': for PASS permits, driver licensing status, or regulatory RAG lookups.\n"
            f"- 'route_optimization': for route deviations, detours, GPS offline warnings, bus delays, or capacity balancing.\n"
            f"- 'executive': for summaries, analytics, overall metrics, or performance ratios.\n"
            f"Next step (exactly one word: safety, compliance, route_optimization, executive):"
        )
        llm_decision = call_gemini(
            prompt=routing_prompt,
            system_instruction="You are the Routing Supervisor for the ADEK School Transportation platform.",
        )
        cleaned = llm_decision.strip().lower() if llm_decision else ""
        if cleaned in ["safety", "compliance", "route_optimization", "executive"]:
            next_step = cleaned
        else:
            # Fallback logic
            if any(w in query.lower() for w in ["deviation", "route", "gps", "delay", "capacity"]):
                next_step = "route_optimization"
            elif any(w in query.lower() for w in ["handover", "guardian", "policy"]):
                next_step = "compliance"
            elif any(w in query.lower() for w in ["phone", "mobile", "distraction", "speed"]):
                next_step = "safety"
            else:
                next_step = "executive"

    # Dynamic LLM instruction coordination text
    llm_msg = call_gemini(
        prompt=f"A user requested scenario {scenario} with query '{query}'. Act as the Supervisor and output a 1-sentence message coordinating this pipeline. Next agent is '{next_step}'. Keep it professional.",
        system_instruction="You are the Supervisor Agent for the ADEK School Transportation AI Compliance Platform.",
    )

    msg = llm_msg or "🧠 Supervisor coordinated execution pipeline."

    # Utilizing LangGraph operator.add reducer by returning only the appended history list item
    return {
        "conversation_history": [{"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router"}],
        "next_step": next_step
    }
