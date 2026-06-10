# Supervisor Agent API Integration Guide

## Overview
The Supervisor Agent is the central LangGraph orchestrator for the ADEK School Transportation AI Compliance Platform. Rather than acting as a traditional chatbot for end-users, the Supervisor acts as a **headless AI orchestrator** that sits behind your existing management infrastructure. It receives raw incident payloads and webhooks from existing systems (like edge cameras, telematics, or manual inspections) and autonomously routes them to specialist agents (Safety, Compliance, Fleet, Evidence) for automated resolution.

## Architecture & Workflow
1. **Event Reception**: External systems trigger the supervisor via the REST API.
2. **Context Parsing**: The Supervisor reads the `event_payload` and the `event_timestamp`. 
3. **LLM Classification**: Using a Google Gemini LLM prompt, the Supervisor dynamically classifies the nature of the event and decides the optimal specialist agent.
4. **Resilient Fallback**: If the LLM rate-limits or fails, the Supervisor falls back to a deterministic keyword-matching system.
5. **Agent Handoff**: The LangGraph state is updated, and the chosen specialist agent takes control.

## API Integration

### Endpoint
`POST /api/agents/supervisor/event`

### JSON Payload Schema
```json
{
  "scenario_id": 99,
  "event_payload": "Webhook: GPS indicates Bus AU-BUS-140 has deviated from the approved route by 2 miles.",
  "event_timestamp": "2026-06-10T12:00:00Z"
}
```

### Parameters
* **`scenario_id`** (int, required): Use `99` for live dynamic events. (IDs 0-3 are reserved for system demo fallbacks).
* **`event_payload`** (str, optional): A text dump or natural language string of the system event.
* **`event_timestamp`** (str, optional): ISO-8601 formatted timestamp of when the incident occurred. If omitted, the backend will auto-generate a UTC timestamp at the millisecond the request is received.

## Autonomous Routing Destinations
The LLM classifies events into exactly one of the following specialist agents:
* **`evidence`**: Edge telemetry, collision data, harsh braking.
* **`safety`**: Driver distraction, speeding, immediate unsafe driving behavior.
* **`compliance`**: Driver permits, certification status, RAG policy lookups.
* **`route_optimization`**: Route deviations, route performance, detour analytics.
* **`fleet_monitoring`**: Active fleet GPS, student boarding/deboarding tracking, capacity.
* **`executive`**: Operational KPIs, analytics, summaries.

## Fallback Logic Definitions
If LLM classification fails, the Supervisor relies on these strict substring matching rules against the `event_payload`:
* `analyze incident`, `evidence`, `telemetry`, `collision`, `harsh`, `braking` -> **evidence agent**
* `gps`, `capacity`, `occupancy`, `fleet`, `utilization`, `boarding` -> **fleet_monitoring agent**
* `deviation`, `route`, `delay`, `performance` -> **route_optimization agent**
* `handover`, `guardian`, `policy`, `permit`, `training`, `compliance` -> **compliance agent**
* `phone`, `mobile`, `distraction`, `speed`, `unsafe` -> **safety agent**
* *(default)* -> **executive agent**
