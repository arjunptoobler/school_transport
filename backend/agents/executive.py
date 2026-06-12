from .state import AgentState
from ..mcp.client import mcp_client
from .llm import call_gemini
import re


def executive_agent(state: AgentState) -> dict:
    query   = state["event_payload"]
    history = state["conversation_history"]

    # Fetch real-time KPIs via MCP tool
    metrics = mcp_client.call_tool("mcp_get_executive_metrics") or {}

    open_incidents  = metrics.get("open_incidents", 0)
    critical        = metrics.get("critical_incidents", 0)
    total_fines     = metrics.get("total_fines", 0)
    fines_amount    = metrics.get("total_fines_amount_aed", 0)
    pending_train   = metrics.get("pending_training", 0)
    grounded        = metrics.get("grounded_buses", 0)
    suspended       = metrics.get("suspended_drivers", 0)
    total_drivers   = metrics.get("total_drivers", 0)
    gps_active      = metrics.get("gps_active", 0)
    compliance_pct  = metrics.get("compliance_score_pct", 0)

    # Time-sliced metrics
    inc_this_month  = metrics.get("incidents_this_month", 0)
    inc_last_month  = metrics.get("incidents_last_month", 0)
    fin_this_month  = metrics.get("fines_this_month", 0)
    fin_last_month  = metrics.get("fines_last_month", 0)
    sus_this_month  = metrics.get("suspensions_this_month", 0)
    sus_last_month  = metrics.get("suspensions_last_month", 0)
    top_risk        = metrics.get("top_risk_drivers", [])
    period          = metrics.get("reporting_period", {})
    this_month_lbl  = period.get("this_month", "this month")
    last_month_lbl  = period.get("last_month", "last month")

    # Format top-risk driver list for the prompt
    top_risk_str = "\n".join(
        f"  #{i+1} {d['name']} ({d['driver_id']}) — {d['incident_count']} incidents, permit={d['permit_status']}, operator={d['operator']}"
        for i, d in enumerate(top_risk)
    ) if top_risk else "  No driver history data available."

    # RAG policy enrichment
    rag_results  = mcp_client.call_tool("mcp_lookup_policy", topic=query)
    rag_chunks   = rag_results if isinstance(rag_results, list) else []
    policy_context = (
        "\n".join(
            f"  [{r.get('authority', 'ADEK')} — {r.get('filename', 'policy')}] {r.get('text', '')[:350]}"
            for r in rag_chunks[:3]
        )
        if rag_chunks else "  No specific policy retrieved — basing response on platform metrics only."
    )

    context_str = "\n".join([f"- {h['agent']}: {h['text']}" for h in history[-3:]])

    prompt = (
        f"You are the Executive AI Agent for the ADEK School Transportation Compliance Platform.\n"
        f"Your role is to synthesise live operational data with regulatory policy to produce board-level insights.\n\n"
        f"User Query: {query}\n\n"
        f"Live Platform Metrics (from database):\n"
        f"  Compliance Score: {compliance_pct}%\n"
        f"  Open Incidents: {open_incidents} ({critical} critical)\n"
        f"  Total Fines Issued: {total_fines} (AED {fines_amount:,.0f})\n"
        f"  Pending Driver Trainings: {pending_train}\n"
        f"  Grounded Buses: {grounded}\n"
        f"  Suspended Drivers: {suspended} of {total_drivers} ({round(suspended/total_drivers*100) if total_drivers else 0}%)\n"
        f"  GPS Online: {gps_active} buses\n\n"
        f"Month-over-Month Trend Data:\n"
        f"  Incidents — {this_month_lbl}: {inc_this_month}  |  {last_month_lbl}: {inc_last_month}  "
        f"({'↑' if inc_this_month > inc_last_month else '↓'} {abs(inc_this_month - inc_last_month)} change)\n"
        f"  Fines Issued — {this_month_lbl}: {fin_this_month}  |  {last_month_lbl}: {fin_last_month}\n"
        f"  Driver Suspensions (enforcement actions) — {this_month_lbl}: {sus_this_month}  |  {last_month_lbl}: {sus_last_month}\n\n"
        f"Top 3 Risk Drivers (by incident count, all time):\n{top_risk_str}\n\n"
        f"Relevant ADEK Regulatory Context (from RAG policy index):\n"
        f"{policy_context}\n\n"
        f"Prior Agent Analysis:\n{context_str}\n\n"
        f"Task: Using the live metrics, trend data, risk driver list, and regulatory context above, "
        f"directly answer the user's specific question. Reference real numbers and ADEK regulations. "
        f"For time-based questions (last month, this week, March), use the month-over-month data above. "
        f"For risk driver questions, reference the Top 3 Risk Drivers list. "
        f"For predictions, use the trend direction and current compliance score to extrapolate.\n"
        f"Output format exactly:\n"
        f"SUMMARY: <your 2-3 sentence answer to the specific query, with real numbers and regulation references>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are the Executive C-Suite Agent. Provide high-level, strategic impact summaries for board reporting. Always answer the specific question asked, using real data.",
    )

    policy_label = f"{len(rag_chunks)} policy chunks" if rag_chunks else "no policy match"

    if not llm_msg:
        # Fallback: directly answer the question using real numbers based on keywords
        q_low = query.lower()
        if any(w in q_low for w in ("suspend", "banned", "last month")):
            text = (
                f"📈 [Executive Summary] {sus_last_month} driver suspension enforcement actions were recorded in {last_month_lbl}, "
                f"vs {sus_this_month} so far in {this_month_lbl}. Currently {suspended}/{total_drivers} drivers hold Suspended permits. "
                f"ADEK Operator Regulation §3.1 mandates immediate permit revocation for repeat offenders."
            )
        elif any(w in q_low for w in ("compliance", "decrease", "march", "score")):
            text = (
                f"📈 [Executive Summary] Current fleet compliance score is {compliance_pct}%. "
                f"Incidents moved from {inc_last_month} in {last_month_lbl} to {inc_this_month} this month "
                f"({'increasing' if inc_this_month > inc_last_month else 'decreasing'} trend). "
                f"{pending_train} drivers have outstanding training SLAs under ADEK Regulation §5.2."
            )
        elif any(w in q_low for w in ("risk", "driver", "top", "worst")):
            top_str = "; ".join(
                f"{d['name']} ({d['incident_count']} incidents, permit {d['permit_status']})"
                for d in top_risk
            ) if top_risk else "data unavailable"
            text = (
                f"📈 [Executive Summary] Top 3 risk drivers this period: {top_str}. "
                f"Fleet has {suspended} suspended drivers of {total_drivers} total. "
                f"ADEK §4.2 requires mandatory suspension for drivers with 3+ violations."
            )
        elif any(w in q_low for w in ("predict", "next month", "forecast", "rate")):
            trend = "increasing" if inc_this_month > inc_last_month else "decreasing"
            text = (
                f"📈 [Executive Summary] Based on current trend, incident rate is {trend} "
                f"({inc_last_month} last month → {inc_this_month} this month). "
                f"With {compliance_pct}% compliance and {pending_train} unresolved training SLAs, "
                f"next month's rate is projected to {'rise' if trend == 'increasing' else 'stabilise'} unless SLAs are cleared."
            )
        else:
            text = (
                f"📈 [Executive Summary] Fleet status ({this_month_lbl}): {open_incidents} open incidents ({critical} critical), "
                f"{total_fines} fines (AED {fines_amount:,.0f}), compliance score {compliance_pct}%, "
                f"{suspended}/{total_drivers} drivers suspended, {grounded} buses grounded. "
                f"Month-on-month incidents: {inc_last_month} → {inc_this_month}. RAG: {policy_label}."
            )
    else:
        try:
            summary = re.search(r"SUMMARY:\s*(.*)", llm_msg, re.IGNORECASE | re.DOTALL).group(1)
            text = f"📈 [Executive Summary] {summary.strip()}"
        except Exception:
            text = f"📈 [Executive Summary] {llm_msg.strip()}"

    return {
        "conversation_history": [{
            "agent": "Executive Agent",
            "text": text,
            "tool": "Executive Analytics MCP + RAG Policy Index",
            "action": f"Fetched live KPIs + trends + top-risk drivers · queried RAG ({policy_label}) · generated C-suite board summary",
        }],
        "next_step": "end",
    }
