# Regulatory and Functional Gap Analysis

A comparison between the specifications in the official *Agentic AI Enabled School Transportation Safety & Compliance Platform Project Scope* and our current implementation.

---

## 1. Missing Agent: Route Optimization Agent
*   **Specification (Section 3.6 & 4)**: Defines a specialized **Route Optimization Agent** responsible for dynamic route planning, capacity balancing, reducing kilometers travelled, and responding to traffic anomalies.
*   **Current State**: Completely missing from our LangGraph orchestration graph. Our graph only registers: `supervisor`, `safety`, `compliance`, `incident`, and `executive` agents.
*   **Impact**: Dynamic route adjustments or capacity planning scenarios in the dashboard currently run on static mocks rather than LLM-driven graph routing.

---

## 2. Missing Workflow: 5-Day compliance SLA Countdown
*   **Specification (Section 3.4)**: If a safety infraction occurs, the driver is assigned mandatory training. If the driver fails to complete the course within **5 days**, the system must automatically execute a suspension escalation workflow (marking the driver permit as restricted in the database and triggering alerts).
*   **Current State**: While we store permit and training columns, we do not have an active countdown or SLA tracker table in SQLite, nor an autonomous scheduler checking and updating training expiry state.

---

## 3. Missing Transaction: Fine Management MCP Tool
*   **Specification (Section 3.8 & 6)**: The platform must support automated integration with government finance and traffic systems to issue fines for regulatory violations (e.g. issuing the DMT AED 5,000 fine for driver mobile distraction or AED 3,000 for speeding).
*   **Current State**: Our MCP tool registry has driver/vehicle query and update capabilities, but lacks a dedicated `mcp_issue_fine_ticket` tool.

---

## 4. Missing Telemetry: Edge AI ADAS Sensor Schema
*   **Specification (Section 3.2)**: Edge devices within buses must transmit standardized telemetry packages including Collision/Impact events, ADAS camera confidence scores, accelerometer deceleration metrics (harsh braking), and incident evidence files.
*   **Current State**: We rely on high-level textual trigger descriptions in the route state rather than structured telemetry packets (x/y/z accelerometer inputs, confidence thresholds, and binary evidence link schemas).
