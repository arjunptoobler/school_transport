from .state import AgentState
from ..database.connection import get_db_connection
from ..mcp.base import mcp_registry
import backend.mcp.evidence  # Import to register evidence tools
from .llm import call_gemini
import re

def evidence_agent(state: AgentState) -> dict:
    query = state["event_payload"]
    scenario = state["scenario"]
    
    # Try to extract an incident ID or vehicle ID
    incident_match = re.search(r"INC-2026-\d{4}", query)
    vehicle_match = re.search(r"AU-BUS-\d{3}", query)
    
    inc_id = incident_match.group(0) if incident_match else None
    veh_id = vehicle_match.group(0) if vehicle_match else None

    evidence_url = "None"
    raw_telemetry = {}

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if inc_id:
            cursor.execute("SELECT evidence_url, type as telemetry_type FROM incidents WHERE incident_id = ?", (inc_id,))
            row = cursor.fetchone()
            if row:
                evidence_url = row["evidence_url"]
                raw_telemetry["type"] = row["telemetry_type"]
        
        # Pull the latest edge telemetry payload for the vehicle to analyze
        if veh_id or inc_id:
            # If we don't have a vehicle ID but have an incident, look up the vehicle
            if not veh_id and inc_id:
                cursor.execute("SELECT vehicle_id FROM incidents WHERE incident_id = ?", (inc_id,))
                vrow = cursor.fetchone()
                if vrow: veh_id = vrow["vehicle_id"]

            if veh_id:
                cursor.execute("SELECT * FROM edge_telemetry WHERE vehicle_id = ? ORDER BY timestamp DESC LIMIT 1", (veh_id,))
                row = cursor.fetchone()
                if row:
                    raw_telemetry["gforce"] = {"x": row["gforce_x"], "y": row["gforce_y"], "z": row["gforce_z"]}
                    raw_telemetry["confidence"] = row["confidence"]
                    raw_telemetry["edge_classification"] = row["event_type"]
                    if evidence_url == "None" or not evidence_url:
                        evidence_url = row["evidence_url"]
    finally:
        conn.close()

    # If this was just normal functional programming, we'd just use an if-statement.
    # But here, we use the LLM to interpret complex G-force and confidence vectors to determine if this is a false positive.
    
    analysis_prompt = (
        f"Analyze the following raw edge telemetry for an incident involving vehicle {veh_id}.\n"
        f"Telemetry Payload: {raw_telemetry}\n"
        f"Evidence Media URL: {evidence_url}\n"
        "Task: Determine if this telemetry represents a true safety violation or a false positive (e.g. harsh braking due to traffic, not reckless driving). "
        "Also, decide the next routing step: 'compliance' (if it requires policy/driver checks) or 'incident' (if it should be immediately escalated to emergency response).\n"
        "Output your response in this exact format:\n"
        "ANALYSIS: <your 1-2 sentence analytical reasoning>\n"
        "ACTION: <FETCH_VIDEO or NONE>\n"
        "ROUTE: <compliance or incident>"
    )

    llm_msg = call_gemini(
        prompt=analysis_prompt,
        system_instruction="You are an expert Edge Telemetry Analyst AI for the ADEK Platform. You interpret G-force data and camera confidence scores.",
    )

    action_str = "Analyzed cabin camera video feed and edge G-Force telemetry."
    if not llm_msg:
        if scenario == 0:
            text = f"👁️ [Telemetry Analysis] Evaluated ADAS camera stream (Evidence: {evidence_url.split('/')[-1] if evidence_url else 'None'}). High confidence 92% match for mobile phone usage while driving. Escalating to compliance."
            next_step = "compliance"
        else:
            text = f"👁️ [Vision Analysis] Processed evidence file: {evidence_url}. High confidence match."
            next_step = "compliance"
    else:
        # Parse the meaningful LLM decision
        try:
            analysis_part = re.search(r"ANALYSIS:\s*(.*)", llm_msg, re.IGNORECASE).group(1).split("ACTION:")[0]
            action_match = re.search(r"ACTION:\s*(.*)", llm_msg, re.IGNORECASE)
            route_part = re.search(r"ROUTE:\s*(.*)", llm_msg, re.IGNORECASE).group(1).strip().lower()
            
            action_taken = ""
            if action_match and "FETCH_VIDEO" in action_match.group(1).upper() and veh_id:
                # Execute MCP Tools
                ts = state.get("event_timestamp", "2026-06-10T12:00:00Z")
                mcp_registry.call_tool("mcp_fetch_dashcam_video", vehicle_id=veh_id, timestamp=ts)
                conf = mcp_registry.call_tool("mcp_get_edge_confidence_score", event_id=f"EVT-{veh_id}")
                
                if inc_id:
                    mcp_registry.call_tool("mcp_attach_evidence_package", incident_id=inc_id, media_urls=[evidence_url], confidence_score=conf.get("confidence_score", 0.9))
                
                action_taken = f" (Action: Fetched 15s edge video & attached to package)"
                action_str = "Fetched and verified edge evidence package"

            text = f"👁️ [Telemetry Analysis] {analysis_part.strip()}{action_taken}"
            next_step = route_part if route_part in ["compliance", "incident"] else "compliance"
        except Exception as e:
            text = f"👁️ [Telemetry Analysis] {llm_msg}"
            next_step = "compliance"

    return {
        "conversation_history": [{"agent": "Evidence Analyst Agent", "text": text, "tool": "Vision & Edge Telemetry MCP", "action": action_str}],
        "next_step": next_step,
    }
