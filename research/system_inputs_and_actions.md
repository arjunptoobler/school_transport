# Agentic System: Inputs and Actions Architecture

This document catalogs the input mechanisms (how the system is triggered) and the available output actions (how the agents mutate state and execute workflows) within the ADEK School Transportation AI Compliance Platform.

---

## 1. System Inputs (Event Triggers)

The multi-agent architecture is strictly event-driven. It operates headlessly, waiting for external systems (edge cameras, parent portals, manual inspection apps) to push events to it.

### Primary Ingestion Endpoint
**`POST /api/agents/supervisor/event`**

**JSON Payload Schema:**
```json
{
  "scenario_id": 99, 
  "event_payload": "Webhook Alert: Guardian not present at drop-off stop #4 for Bus AU-BUS-102.",
  "event_timestamp": "2026-06-10T12:00:00Z"
}
```
* **`scenario_id`** (`int`): Required. Set to 99 for dynamically generated live events.
* **`event_payload`** (`string`): The unstructured raw text, log string, or natural language description of the event.
* **`event_timestamp`** (`string`): ISO-8601 timestamp. If omitted, the backend auto-generates the exact millisecond time of receipt.

---

## 2. System Actions (MCP Tool Registry)

Agents do not execute hardcoded Python scripts directly; they utilize the **Model Context Protocol (MCP)** to interact with the outside world. This creates a secure, deterministic boundary for LLM execution. 

Below are the registered MCP actions categorized by domain:

### Fleet Operations (`backend/mcp/fleet.py`)
* **`mcp_get_vehicle_status`**: (Read) Fetches live vehicle details, GPS coordinates, route assignment, and current passenger manifest.
* **`mcp_update_inspection_status`**: (Write) Updates the database with pre-trip or post-trip safety inspection results.
* **`mcp_log_student_boarding`**: (Write) Logs a student onboarding or offboarding event against a specific bus stop.

### Route Optimization (`backend/mcp/route.py`)
* **`mcp_calculate_detour`**: (Read/Compute) Calculates a dynamic spatial detour to avoid hazards/traffic, returning new linestring geometry and expected delay.
* **`mcp_update_bus_schedule`**: (Write) Mutates the ETA schedule in the database for all subsequent downstream stops.
* **`mcp_broadcast_eta_change`**: (Write) Triggers push notifications to parent apps notifying them of the dynamically calculated delay.

### Incident Management (`backend/mcp/incident.py`)
* **`mcp_create_incident`**: (Write) Generates a formal, tracked emergency ticket (requires severity level, incident type, and description).
* **`mcp_get_open_incidents`**: (Read) Retrieves unresolved tickets to provide historical context to agents.
* **`mcp_update_incident_status`**: (Write) Formally closes, resolves, or escalates an existing incident ID.
* **`mcp_flag_for_manual_override`**: (Write) Halts autonomous execution and flags an incident for mandatory Human-in-the-Loop review by the Command Center.

### Compliance & Enforcement (`backend/mcp/compliance.py`)
* **`mcp_issue_fine_ticket`**: (Write) Formally registers a monetary fine or warning against a driver or operating vendor.
* **`mcp_assign_training_sla`**: (Write) Enforces mandatory remedial training, assigning a strict Service Level Agreement (SLA) deadline date.
* **`mcp_check_sla_compliance`**: (Read/Execute) Automatically audits if assigned training deadlines have been met, triggering further penalties if breached.
* **`mcp_submit_adek_compliance_report`**: (Write) Submits a formal violation report to external ADEK/Government portals via API.
* **`mcp_sync_permit_status_with_gov`**: (Write) Synchronizes the internal permit suspension status with the external government licensing ledger.
* **`mcp_ingest_edge_telemetry`**: (Read/Write) Ingests raw hardware telemetry arrays from the bus's edge IoT systems.
* **`mcp_fetch_dashcam_video`**: (Read) Retrieves specific 15-second video clips from the bus edge DVR corresponding to an event timestamp.
* **`mcp_get_edge_confidence_score`**: (Read) Retrieves the raw neural network confidence score for a detected safety event.
* **`mcp_attach_evidence_package`**: (Write) Compiles video URLs and telemetry scores into an immutable evidence package attached to an incident.

### Driver Management (`backend/mcp/driver.py`)
* **`mcp_get_driver_record`**: (Read) Pulls the driver's ADEK permit status, training history, and past infractions.
* **`mcp_update_driver_status`**: (Write) Mutates driver licensing state (e.g., instantly suspending a permit or flagging it for review).

### Policy Knowledge / RAG (`backend/mcp/policy.py`)
* **`mcp_lookup_policy`**: (Read) Performs a semantic vector-search (ChromaDB) across the massive unstructured text of the official ADEK 2026 Transportation Regulations.
* **`mcp_get_violation_matrix`**: (Read) Fetches predefined deterministic penalty structures (e.g., exact fine amounts for specific infractions).

### Notifications (`backend/mcp/notification.py`)
* **`mcp_send_sms`**: (Write) Dispatches an urgent SMS directly to a student's assigned guardian or a fleet operator.
* **`mcp_send_push`**: (Write) Pushes an alert notification to the driver's mobile console or the parent app.
