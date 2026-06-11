# Safety Agent Capabilities Overview

The **Safety Agent** (`backend/agents/safety.py`) acts as the immediate "first responder" for physical risks within the LangGraph architecture. It evaluates incoming incident events specifically for physical threats to student passengers and vehicles.

## Core Capabilities

1. **Context Enrichment (via MCP)**
   When it receives an event payload (e.g., "Bus swerved"), it automatically extracts entities like `vehicle_id` and uses Model Context Protocol (MCP) tools to query the live fleet database for the bus's current status. It also fetches the associated student manifest to understand exactly who is on board during the incident.

2. **Risk Classification**
   Powered by a Google Gemini LLM prompted as an "expert Transportation Safety Officer," it analyzes the situational data and explicitly classifies the physical threat level to students as **High**, **Medium**, or **Low**.

3. **Immediate Action Recommendation**
   It formulates an immediate, tactical safety response designed to neutralize the threat (e.g., "Stop the bus immediately," "Contact the assigned guardian," or "Ignore if safe to proceed").

4. **Triaging & Autonomous Handoff**
   Once it assesses the physical safety, it dynamically routes the workflow state to the next appropriate specialist agent:
   - ➔ **Evidence Agent**: Selected if the Safety Agent suspects an issue (like harsh braking) but needs to verify the claim via cabin camera footage or IoT edge telemetry.
   - ➔ **Compliance Agent**: Selected if the physical safety risk is low, but an ADEK protocol was breached (e.g., the driver missed a mandatory training module).
   - ➔ **Incident Agent**: Selected if the situation is classified as a severe emergency requiring an immediate ticket creation and automated stakeholder escalation.
