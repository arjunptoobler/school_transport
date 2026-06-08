from .state import AgentState
from ..database.connection import get_db_connection


def executive_agent(state: AgentState) -> AgentState:
    history = state["conversation_history"]
    scenario = state["scenario"]

    if scenario == 0:
        # Dynamically fetch stats to calculate fleet safety
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents")
        total_incidents = cursor.fetchone()[0]
        conn.close()

        # Calculate a simulated metric from actual data
        simulated_score = max(70.0, round(100.0 - (total_incidents * 0.05), 1))

        msg = f"📊 Logged. Fleet safety index calculated at {simulated_score}% based on {total_incidents} logged events. Recommending immediate driver stand-down."
        tool = "Analytics MCP"
    elif scenario == 3:
        # Query database to aggregate real stats
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
        pending_training = cursor.fetchone()[0]
        conn.close()

        pending_ratio = round((pending_training / total_drivers) * 100, 1)

        msg = f"📊 Synthesizing executive report. Compliance metrics analyzed across {total_drivers} drivers. Main threat factor: {pending_training} drivers ({pending_ratio}%) have pending safe-driving certifications."
        tool = "Analytics MCP"
    else:
        msg = "📊 Executive report compiled. Safety indices are within target threshold."
        tool = "Analytics MCP"

    history.append({"agent": "Executive Agent", "text": msg, "tool": tool})
    return {**state, "conversation_history": history, "next_step": "end"}
