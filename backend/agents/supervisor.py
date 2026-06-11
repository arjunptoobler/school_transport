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
    
    # If the LLM returned a valid agent, use it. Otherwise, use a smart keyword fallback (for rate limits).
    if cleaned in AGENT_REGISTRY:
        next_step = cleaned
    else:
        ep = event_payload.lower()
        if "seatbelt" in ep or "distraction" in ep or "speeding" in ep or "safety" in ep or "mobile" in ep or "phone" in ep or "device" in ep or "camera" in ep:
            next_step = "safety"
        elif "collision" in ep or "telemetry" in ep or "brake" in ep:
            next_step = "evidence"
        elif "permit" in ep or "compliance" in ep or "inspection" in ep:
            next_step = "compliance"
        elif "route" in ep or "detour" in ep or "schedule" in ep:
            next_step = "route_optimization"
        elif "guardian" in ep or "capacity" in ep or "boarding" in ep:
            next_step = "fleet_monitoring"
        else:
            next_step = "executive"

    # To eliminate unnecessary LLM latency (saving 1-2 seconds), we generate the coordination message deterministically
    msg = f"🧠 Analyzed event payload and dynamically routed workflow to '{next_step}' specialist agent."

    # Utilizing LangGraph operator.add reducer by returning only the appended history list item
    return {
        "event_payload": event_payload,
        "conversation_history": [{"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router", "action": f"Routed workflow autonomously to '{next_step}' agent."}],
        "next_step": next_step
    }
