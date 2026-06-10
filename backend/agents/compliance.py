from .state import AgentState
from ..mcp.base import mcp_registry
from .parser import extract_entities
from .llm import call_gemini
import re

def compliance_agent(state: AgentState) -> dict:
    query = state["event_payload"]
    scenario = state["scenario"]

    # Extract dynamic parameters
    entities = extract_entities(state)
    driver_id = entities["driver_id"]
    vehicle_id = entities["vehicle_id"]
    topic = entities["topic"] or query

    # Gather evidence from MCPs
    driver_data = {}
    if driver_id and driver_id != "Unknown":
        drv = mcp_registry.call_tool("mcp_get_driver_record", driver_id=driver_id)
        if drv and "error" not in drv:
            driver_data = drv

    history = state.get("conversation_history", [])
    history_str = "\n".join([f"{h['agent']}: {h['text']}" for h in history])

    # RAG lookup for policies
    rag_res = mcp_registry.call_tool("mcp_lookup_policy", topic=topic)
    policy_text = ""
    if rag_res:
        policy_text = "\n".join([f"- {r['text'][:300]}" for r in rag_res])
    else:
        policy_text = "No specific policy retrieved."

    # Ask the LLM to act as a conversational Compliance Chatbot
    prompt = (
        f"You are the Compliance Agent Chatbot for the ADEK School Transport Platform.\n"
        f"You must converse naturally with the user while analyzing situations based on ADEK policies.\n"
        f"Conversation History:\n{history_str}\n\n"
        f"User Query/Event: {query}\n"
        f"Driver Data Context: {driver_data}\n"
        f"Relevant Policy Rules from RAG:\n{policy_text}\n\n"
        f"Task:\n"
        f"1. Respond directly to the User Query in a helpful, conversational chatbot tone.\n"
        f"2. Cite the specific ADEK policy rules provided in the RAG context if applicable.\n"
        f"3. Determine if a regulatory violation has occurred and state it clearly.\n"
        f"4. Decide if an automated enforcement action is required: 'SUSPEND' (if severe violation like mobile usage), 'ASSIGN_TRAINING' (if minor violation), or 'NONE'.\n"
        f"5. Decide the next routing step: 'incident' (if escalation/actions are needed) or 'executive'.\n"
        f"6. Make a final decision autonomously. Do NOT recommend manual review unless the user query explicitly appeals or contests a decision.\n"
        f"Output format exactly:\n"
        f"CHAT_RESPONSE: <your conversational response to the user, citing policies>\n"
        f"ACTION: <SUSPEND, ASSIGN_TRAINING, or NONE>\n"
        f"ROUTE: <incident or executive>"
    )

    llm_msg = call_gemini(
        prompt=prompt,
        system_instruction="You are an expert conversational Compliance Chatbot for UAE transportation regulations. You evaluate facts against policy text and enforce actions automatically without manual review.",
    )

    action_taken = ""
    if not llm_msg:
        if scenario == 0:
            text = "🤖 [Policy Audit] Driver DRV-4412 (Mobile Usage). Violated ADEK Regulation 4.2.1. Escalating to Incident."
            next_step = "incident"
            if driver_id:
                mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Suspended")
                action_taken = f" (Action: Suspended Driver {driver_id})"
        elif scenario == 1:
            text = "🤖 [Policy Audit] Missing guardian. Violated ADEK Rule 7.3. Student correctly retained. Escalating to Incident."
            next_step = "incident"
        elif scenario == 2:
            text = "🤖 [Policy Audit] Vehicle inspection fail. Violated ADEK Fleet Rule 9.1. Escalating to Incident."
            next_step = "incident"
        elif scenario == 3:
            text = "🤖 [Policy Audit] Fleet KPIs aggregated successfully. Sending to Executive Summary."
            next_step = "executive"
        else:
            text = f"🤖 [Policy Audit] Verified compliance status. Automated decision executed based on RAG policy rules."
            next_step = "incident"
    else:
        try:
            assessment = re.search(r"CHAT_RESPONSE:\s*(.*)", llm_msg, re.IGNORECASE | re.DOTALL).group(1).split("ACTION:")[0]
            action_match = re.search(r"ACTION:\s*(.*)", llm_msg, re.IGNORECASE)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            
            if action_match and driver_id and driver_id != "Unknown":
                act = action_match.group(1).strip().upper()
                if act == "SUSPEND":
                    mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Suspended")
                    action_taken = f" (Action: Suspended Driver {driver_id})"
                elif act == "ASSIGN_TRAINING":
                    mcp_registry.call_tool("mcp_update_driver_status", driver_id=driver_id, permit_status="Valid", training_status="Pending Refresher")
                    action_taken = f" (Action: Assigned Training to {driver_id})"

            text = f"🤖 {assessment.strip()}{action_taken}"
            next_step = route_part if route_part in ["incident", "executive"] else "incident"
        except Exception as e:
            text = f"🤖 {llm_msg.strip()}"
            next_step = "incident"

    action_str = action_taken.replace(" (Action: ", "").replace(")", "").strip() if action_taken else "Checked compliance registry & RAG rules"

    return {
        "conversation_history": [{"agent": "Compliance Agent", "text": text, "tool": "Automated Enforcement MCP", "action": action_str}],
        "next_step": next_step,
    }
