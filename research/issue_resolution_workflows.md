# ADEK Agentic Issue Resolution Workflows

This document maps all possible issue triggers (system events) to their corresponding autonomous resolution workflows executed by the LangGraph multi-agent architecture.

---

## 1. Driver Safety & Distraction Events
**Event Triggers:** Dashcam flags, edge IoT triggers containing keywords like `distraction`, `seatbelt`, `speeding`, `mobile`, `phone`, `camera`.

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Classifies as a critical safety event and routes to Safety.
2. **Safety Agent:** Analyzes the telemetry and determines the severity of the driver's behavior.
3. **Evidence Agent:** Interfaces with the edge DVR (via MCP) to pull 15-second video clips and confidence scores, attaching an immutable evidence package.
4. **Compliance Agent:** Performs a semantic RAG lookup against ADEK transportation policies to find the exact penalty clause. 
5. **Incident Agent:** Creates an official High-Severity Incident, executes fines, flags the driver's permit for suspension, and notifies the vendor.

---

## 2. Route Deviations & Roadblocks
**Event Triggers:** API webhooks or traffic system alerts containing `route`, `detour`, `schedule`, `block`.

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Identifies route disruption and hands off to Route Optimization.
2. **Route Optimization Agent:** Calls external mapping MCPs to calculate the most efficient detour spatial geometry.
3. **Execution:** It then autonomously updates the ETA schedules in the database and broadcasts push notifications to the parent portal advising them of the delay.

---

## 3. Missing Guardian & Boarding Anomalies
**Event Triggers:** Driver tablet inputs or portal flags containing `guardian`, `boarding`, `dropoff`, `capacity`.

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Classifies as a passenger tracking issue and routes to Fleet Monitoring.
2. **Fleet Monitoring Agent:** Checks the vehicle manifest, stops list, and GPS coordinates.
3. **Compliance Agent:** Pulls the ADEK Guardian Handover policy (which mandates students under Grade 3 cannot be left unattended).
4. **Incident Agent:** Instructs the driver to keep the student on the bus, logs a Medium-Severity incident, and fires an urgent SMS directly to the guardian.

---

## 4. Vehicle Hardware & Pre-Trip Compliance Failures
**Event Triggers:** Diagnostic sensors or pre-trip driver logs containing `brake`, `inspection`, `permit`, `compliance`.

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Classifies as a hardware compliance risk.
2. **Evidence Agent:** Reviews edge telemetry (e.g., hydraulic brake pressure drops).
3. **Fleet Monitoring Agent:** Immediately grounds the unsafe vehicle in the fleet database.
4. **Route Optimization Agent:** Identifies the nearest standby bus at the depot and recalculates a merge route to pick up stranded students.
5. **Incident Agent:** Logs the hardware failure and schedules a maintenance ticket.

---

## 5. Duplicate or Flooding Triggers (Alert Fatigue Prevention)
**Event Triggers:** Any incoming webhook for a vehicle/driver that already has an active, unresolved incident.

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Parses the `vehicle_id` and `driver_id` from the payload.
2. **Deduplication Engine:** Queries the SQLite database for open incidents (`status != 'Resolved'`).
3. **Execution:** Immediately halts the LangGraph workflow, outputting `Halted workflow to prevent alert fatigue`, bypassing all downstream LLMs and preventing duplicate ticketing.

---

## 6. Executive & General Fallback
**Event Triggers:** Unrecognized natural language queries or high-level questions (e.g., "Why did compliance drop?").

**Autonomous Workflow Path:**
1. **Supervisor Agent:** Fails to match specific edge criteria, routes to Executive Agent.
2. **Executive Agent:** Compiles high-level operational KPIs, cross-references recent resolved incidents, and generates a board-level summary report for the Command Center.
