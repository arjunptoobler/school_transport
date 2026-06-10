import operator
from typing import Annotated, Any, Dict, List, TypedDict


class AgentState(TypedDict):
    scenario: int
    event_payload: str
    event_timestamp: str
    current_agent: str
    # Annotated with operator.add forces LangGraph to automatically append new items
    # rather than requiring manual copying and merging in every node.
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    next_step: str
    metadata: Dict[str, Any]
