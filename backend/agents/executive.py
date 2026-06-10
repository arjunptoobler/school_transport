from .state import AgentState
from ..database.connection import get_db_connection
from .llm import call_gemini
import re

def executive_agent(state: AgentState) -> dict:
    query = state["event_payload"]
    history = state["conversation_history"]

    # Gather system metrics
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status != 'Closed'")
        open_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fines")
        total_fines = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE training_status != 'Complete'")
        pending_training = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE inspection_status != 'valid'")
        grounded_buses = cursor.fetchone()[0]
    finally:
        conn.close()

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history])

    prompt = (
        f"You are the Executive AI Agent for the ADEK Platform.\n"
        f"Review the current situation and the analysis from previous agents:\n"
        f"User Query: {query}\n"
        f"Platform Metrics: Open Incidents={open_incidents}, Total Fines={total_fines}, Pending Driver Trainings={pending_training}, Grounded Buses={grounded_buses}\n"
        f"Agent Analysis Context:\n{context_str}\n\n"
        f"Task:\n"
        f"Provide a strategic, C-level executive summary of this situation and its impact on the metrics.\n"
        f"Output format exactly:\n"
        f"SUMMARY: <your 1-2 sentence executive summary>\n"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are the Executive C-Suite Agent. You provide high-level, strategic impact summaries.",
    )

    if not llm_msg:
        scenario = state.get("scenario")
        if scenario == 3:
            text = f"📈 [Executive Summary] Fleet metrics indicate {open_incidents} open incidents and {pending_training} pending driver trainings. Compliance enforcement is actively isolating risks."
        else:
            text = "📈 Executive summary recorded in standard operational metrics."
    else:
        try:
            summary = re.search(r"SUMMARY:\s*(.*)", llm_msg, re.IGNORECASE | re.DOTALL).group(1)
            text = f"📈 [Executive Summary] {summary.strip()}"
        except:
            text = f"📈 [Executive Summary] {llm_msg.strip()}"

    return {
        "conversation_history": [{"agent": "Executive Agent", "text": text, "tool": "Analytics MCP", "action": "Generated executive C-suite dashboard metrics summary"}],
        "next_step": "end",
    }
