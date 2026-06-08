from .base import mcp_registry
from ..rag.vector_db import query_policy

@mcp_registry.register_tool(name="mcp_lookup_policy")
def lookup_policy(topic: str):
    """Retrieve policy regulations by query topic from the vector database."""
    return query_policy(topic)

@mcp_registry.register_tool(name="mcp_get_violation_matrix")
def get_violation_matrix():
    """Get the compliance violation categories and fine structure."""
    return {
        "driver_distraction": {"fine_aed": 5000, "black_points": 24, "action": "Immediate Suspension"},
        "speeding_school_zone": {"fine_aed": 3000, "black_points": 12, "action": "Warning / Retraining"},
        "missing_guardian": {"fine_aed": 0, "black_points": 0, "action": "Retain pupil and contact parent"}
    }
