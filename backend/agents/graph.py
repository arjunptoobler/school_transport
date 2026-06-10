from langgraph.graph import StateGraph, END

from .state import AgentState
from .supervisor import supervisor_agent
from .compliance import compliance_agent
from .safety import safety_agent
from .incident import incident_agent
from .executive import executive_agent
from .route_optimization import route_optimization_agent
from .fleet_monitoring import fleet_monitoring_agent
from .evidence import evidence_agent

# Compiled once at module import — StateGraph.compile() is safe to reuse across requests
_agent_graph = None


def _build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor",  supervisor_agent)
    workflow.add_node("safety",      safety_agent)
    workflow.add_node("evidence",    evidence_agent)
    workflow.add_node("compliance",  compliance_agent)
    workflow.add_node("route_optimization", route_optimization_agent)
    workflow.add_node("fleet_monitoring", fleet_monitoring_agent)
    workflow.add_node("incident",    incident_agent)
    workflow.add_node("executive",   executive_agent)

    workflow.set_entry_point("supervisor")

    def route_next(state: AgentState):
        nxt = state["next_step"]
        return END if nxt == "end" else nxt

    edges = {
        "safety": "safety",
        "evidence": "evidence",
        "compliance": "compliance",
        "route_optimization": "route_optimization",
        "fleet_monitoring": "fleet_monitoring",
        "incident": "incident",
        "executive": "executive",
        END: END
    }

    workflow.add_conditional_edges("supervisor",  route_next, edges)
    workflow.add_conditional_edges("safety",      route_next, {**edges})
    workflow.add_conditional_edges("evidence",    route_next, {**edges})
    workflow.add_conditional_edges("route_optimization", route_next, {**edges})
    workflow.add_conditional_edges("fleet_monitoring", route_next, {**edges})
    workflow.add_conditional_edges("compliance",  route_next, {**edges})
    workflow.add_conditional_edges("incident",    route_next, {**edges})
    workflow.add_conditional_edges("executive",   lambda _: END, {END: END})

    return workflow.compile()


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = _build_graph()
    return _agent_graph


def run_agentic_flow(scenario_id: int, event_payload: str = "", event_timestamp: str = "") -> list:
    import datetime
    
    # Auto-generate a timestamp if not provided by the API/System
    if not event_timestamp:
        event_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
    graph = get_agent_graph()
    initial_state = AgentState(
        scenario=scenario_id,
        event_payload=event_payload,
        event_timestamp=event_timestamp,
        current_agent="Supervisor Agent",
        conversation_history=[],
        next_step="supervisor",
        metadata={},
    )
    result = graph.invoke(initial_state)
    return result["conversation_history"]
