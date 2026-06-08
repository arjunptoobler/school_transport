from .state import AgentState
from ..database.connection import get_db_connection
from .llm import call_gemini


def executive_agent(state: AgentState) -> dict:
    scenario = state["scenario"]

    # Retrieve real metrics from SQLite
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents")
        total_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
        pending_training = cursor.fetchone()[0]
    finally:
        conn.close()

    simulated_score = max(70.0, round(100.0 - (total_incidents * 0.05), 1))
    pending_ratio = round((pending_training / total_drivers) * 100, 1)

    if scenario == 0:
        fallback_msg = f"📊 Logged. Fleet safety index calculated at {simulated_score}% based on {total_incidents} logged events. Recommending immediate driver stand-down."
        tool = "Analytics MCP"
        prompt_desc = f"Distraction infraction occurred. Total incidents: {total_incidents}. Estimated fleet safety score dropped to {simulated_score}%. Recommending stand-down."
    elif scenario == 3:
        fallback_msg = f"📊 Synthesizing executive report. Compliance metrics analyzed across {total_drivers} drivers. Main threat factor: {pending_training} drivers ({pending_ratio}%) have pending safe-driving certifications."
        tool = "Analytics MCP"
        prompt_desc = f"Synthesizing weekly report. Active drivers: {total_drivers}. Pending training: {pending_training} ({pending_ratio}%). Recommended action: split shifts or scheduling adjustments."
    else:
        fallback_msg = "📊 Executive report compiled. Safety indices are within target threshold."
        tool = "Analytics MCP"
        prompt_desc = f"Compliance indices nominal. Active drivers: {total_drivers}. Safety score: {simulated_score}%."

    # Call LLM
    llm_msg = call_gemini(
        prompt=f"Formulate a brief executive summary. Context: {prompt_desc}. Make it formal and concise (1-2 sentences). Do not use greeting or closing sentences.",
        system_instruction="You are the Executive Agent for the ADEK School Transportation Compliance Platform.",
    )

    msg = llm_msg or fallback_msg
    return {
        "conversation_history": [{"agent": "Executive Agent", "text": msg, "tool": tool}],
        "next_step": "end",
    }
