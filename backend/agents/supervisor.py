from .state import AgentState
from .llm import call_gemini


def supervisor_agent(state: AgentState) -> dict:
    event_payload = state["event_payload"]
    # Define A2A Agent Capabilities Registry
    AGENT_REGISTRY = {
        "evidence": "Specializes in analyzing incidents, edge telemetry, collision data, or harsh braking.",
        "safety": "Specializes in handling driver distraction, speeding, or immediate unsafe driving behaviors.",
        "compliance": "Specializes in driver permits, certification status, training workflows, and RAG policy lookups.",
        "route_optimization": "Specializes in route deviations, route performance, detour analytics, or scheduling.",
        "fleet_monitoring": "Specializes in active fleet GPS tracking, student boarding/deboarding, bus capacity, and occupancy.",
        "executive": "Specializes in operational KPIs, high-level analytics, board summaries, and overall metrics."
    }

    # Dynamically build capabilities list for the LLM
    agent_capabilities_str = "\n".join([f"- '{name}': {desc}" for name, desc in AGENT_REGISTRY.items()])
    agent_names = ", ".join(AGENT_REGISTRY.keys())

    # LLM Autonomous routing classification
    routing_prompt = (
        f"Classify the following incoming system event or payload: '{event_payload}'.\n"
        f"Return exactly one word matching the next agent name based on their registered capabilities:\n"
        f"{agent_capabilities_str}\n"
        f"Next step (exactly one word from this list: {agent_names}):"
    )
    llm_decision = call_gemini(
        prompt=routing_prompt,
        system_instruction="You are the Routing Supervisor for the ADEK School Transportation platform.",
    )
    cleaned = llm_decision.strip().lower() if llm_decision else ""
    
    # We explicitly trust the LLM routing decision now. Default to executive if unrecognized.
    next_step = cleaned if cleaned in AGENT_REGISTRY else "executive"

    # Dynamic LLM instruction coordination text
    llm_msg = call_gemini(
        prompt=f"An incident event occurred at timestamp {state.get('event_timestamp', 'UNKNOWN')} with payload '{event_payload}'. Act as the Supervisor and output a 1-sentence message coordinating this pipeline. Next agent is '{next_step}'. Keep it professional.",
        system_instruction="You are the Supervisor Agent for the ADEK School Transportation AI Compliance Platform.",
    )

    msg = llm_msg or "🧠 Supervisor coordinated execution pipeline."

    # Utilizing LangGraph operator.add reducer by returning only the appended history list item
    return {
        "event_payload": event_payload,
        "conversation_history": [{"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router", "action": f"Routed workflow autonomously to '{next_step}' agent."}],
        "next_step": next_step
    }
