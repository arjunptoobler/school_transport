from .state import AgentState
from .llm import call_gemini


def supervisor_agent(state: AgentState) -> dict:
    event_payload = state["event_payload"]
    scenario = state["scenario"]

    # Populate demo queries if missing, but let the LLM dynamically decide the routing!
    if scenario == 0 and not event_payload:
        event_payload = "System Event: Driver using mobile device via cabin camera on Bus AU-BUS-105."
    elif scenario == 1 and not event_payload:
        event_payload = "Webhook Alert: Guardian not present at stop #4 for Bus AU-BUS-102. Student retained."
    elif scenario == 2 and not event_payload:
        event_payload = "Pre-trip compliance check failed. Braking pressure below ADEK safety threshold for Bus AU-BUS-104."
    elif scenario == 3 and not event_payload:
        event_payload = "System trigger: Generate Executive C-Level Summary of platform metrics."

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
    
    if cleaned in AGENT_REGISTRY:
        next_step = cleaned
    else:
        # Fallback logic mapped to PRD requirements if LLM rate limits
        p_lower = event_payload.lower()
        if any(w in p_lower for w in ["analyze incident", "evidence", "telemetry", "collision", "harsh", "braking"]):
            next_step = "evidence"  # PRD 3.2 Edge AI
        elif any(w in p_lower for w in ["gps", "capacity", "occupancy", "fleet", "utilization", "boarding"]):
            next_step = "fleet_monitoring"  # PRD 3.1 Fleet Tracking
        elif any(w in p_lower for w in ["deviation", "route", "delay", "performance"]):
            next_step = "route_optimization"  # PRD 3.6 Route Optimization
        elif any(w in p_lower for w in ["handover", "guardian", "policy", "permit", "training", "compliance"]):
            next_step = "compliance"  # PRD 3.4 Compliance
        elif any(w in p_lower for w in ["phone", "mobile", "distraction", "speed", "unsafe"]):
            next_step = "safety"  # PRD 3.3 Safety Events
        else:
            next_step = "executive"  # PRD 4.0 Analytics

    # Dynamic LLM instruction coordination text
    llm_msg = call_gemini(
        prompt=f"An incident event occurred at timestamp {state.get('event_timestamp', 'UNKNOWN')} in scenario {scenario} with payload '{event_payload}'. Act as the Supervisor and output a 1-sentence message coordinating this pipeline. Next agent is '{next_step}'. Keep it professional.",
        system_instruction="You are the Supervisor Agent for the ADEK School Transportation AI Compliance Platform.",
    )

    msg = llm_msg or "🧠 Supervisor coordinated execution pipeline."

    # Utilizing LangGraph operator.add reducer by returning only the appended history list item
    return {
        "event_payload": event_payload,
        "conversation_history": [{"agent": "Supervisor Agent", "text": msg, "tool": "LangGraph State Router", "action": f"Routed workflow autonomously to '{next_step}' agent."}],
        "next_step": next_step
    }
