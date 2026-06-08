from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    scenario: int
    user_query: str
    current_agent: str
    conversation_history: List[Dict[str, str]]
    next_step: str
    metadata: Dict[str, Any]
