# ADEK School Transportation AI Compliance Platform

Agentic AI system for real-time school bus safety monitoring, regulatory compliance enforcement, and autonomous incident management — built for the Abu Dhabi Department of Education and Knowledge (ADEK).

---

## What This System Does

When a safety or compliance event occurs on the school bus network (a distracted driver, a missing guardian at drop-off, a brake failure, a pre-departure permit violation), the system:

1. Receives the event via the dashboard or an external API call
2. Routes it through a multi-agent LangGraph pipeline
3. Each agent queries real-time data via MCP tools and calls the Gemini LLM for reasoning
4. Actions are executed autonomously — permit suspensions, fines, training SLAs, SMS alerts, standby bus dispatch
5. Everything is written to the database and surfaced on the dashboard in real time

No human needs to manually look up regulations, issue fines, or notify parents. The agents handle it end-to-end in under 30 seconds.

---

## Architecture

```
Frontend (Vanilla HTML/CSS/JS SPA)
        |
        | HTTP REST
        v
FastAPI Backend  (/api/...)
        |
        | LangGraph StateGraph
        v
┌─────────────────────────────────────────────────────────┐
│                   AGENT PIPELINE                         │
│                                                          │
│  Supervisor ──► Safety ──► Evidence ──► Compliance ──►  │
│      │                                      │            │
│      ├──────────────────────────────────►  Incident ──► │
│      │                                      │            │
│      ├──► Fleet Monitoring ──► Route Opt ──►│            │
│      │                                      │            │
│      └──────────────────────────────────►  Executive    │
└─────────────────────────────────────────────────────────┘
        |
        | MCP Protocol (subprocess)
        v
MCP Server (FastMCP) ──► SQLite Database
                    └──► ChromaDB (RAG / policy docs)
                    └──► Notification stubs (SMS, Push)
```

### Key Technology Choices

| Layer | Technology | Why |
|---|---|---|
| Agent orchestration | LangGraph StateGraph | Deterministic routing between agents with conditional edges |
| LLM reasoning | Google Gemini (native function calling) | Structured tool call output without prompt engineering hacks |
| Tool protocol | FastMCP (Model Context Protocol) | Standardized tool interface; MCP server runs as isolated subprocess |
| Database | SQLite (WAL mode) | Zero-config, file-based, concurrent read-safe |
| RAG / Policy | ChromaDB + pypdf | ADEK regulation documents embedded and queried at runtime |
| Backend API | FastAPI | Auto-generates OpenAPI docs at `/docs` |
| Frontend | Vanilla HTML/CSS/JS | No build step, works offline, easy to demo |

---

## Project Structure

```
school_transport/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Environment & path settings
│   ├── agents/
│   │   ├── graph.py             # LangGraph StateGraph definition
│   │   ├── state.py             # AgentState TypedDict
│   │   ├── supervisor.py        # Supervisor Agent — routes all events
│   │   ├── safety.py            # Safety Agent — ADAS camera / behavior analysis
│   │   ├── evidence.py          # Evidence Agent — camera/telemetry ingestion
│   │   ├── fleet_monitoring.py  # Fleet Agent — GPS, occupancy, grounding
│   │   ├── route_optimization.py # Route Agent — detour, standby bus dispatch
│   │   ├── compliance.py        # Compliance Agent — ADEK reg lookup + ruling
│   │   ├── incident.py          # Incident Agent — ticket creation, SMS alerts
│   │   ├── executive.py         # Executive Agent — KPI summary for leadership
│   │   ├── llm.py               # Gemini API wrapper
│   │   └── parser.py            # Entity extractor (driver/vehicle IDs from text)
│   ├── mcp/
│   │   ├── server.py            # FastMCP server entry point
│   │   ├── client.py            # Sync MCP client (called by agents)
│   │   ├── compliance.py        # MCP tools: fines, training SLA, driver status, exec metrics
│   │   ├── driver.py            # MCP tools: driver lookup, permit sync
│   │   ├── fleet.py             # MCP tools: vehicle status, inspection, GPS
│   │   ├── evidence.py          # MCP tools: camera evidence capture, telemetry ingestion
│   │   ├── incident.py          # MCP tools: create/update incident tickets, audit log
│   │   ├── notification.py      # MCP tools: SMS, push notifications
│   │   ├── route.py             # MCP tools: detour calculation, schedule update, ETA broadcast
│   │   └── policy.py            # MCP tools: RAG policy search
│   ├── database/
│   │   ├── models.py            # Table CREATE statements
│   │   ├── seed.py              # Demo data seeder (idempotent)
│   │   ├── connection.py        # SQLite connection factory (WAL mode)
│   │   └── school_transport.db  # Runtime SQLite database (auto-created)
│   ├── rag/
│   │   ├── vector_db.py         # ChromaDB init + query
│   │   ├── ingestion.py         # PDF/txt ingester for policy documents
│   │   └── chroma_db/           # Vector store (auto-created on first run)
│   └── routes/
│       ├── agents.py            # POST /api/agents/run_scenario, reset_demo
│       ├── fleet.py             # GET /api/fleet/status, kpis, fines, slas, routes
│       ├── incidents.py         # GET/POST /api/incidents/
│       └── policy.py            # GET /api/policy/search
├── front/
│   ├── index.html               # Single-page dashboard
│   ├── app.js                   # All frontend logic (API calls, rendering)
│   └── styles.css               # Dark-theme UI styles
├── rag/
│   └── documents/
│       ├── adek/                # ADEK policy PDFs and text files
│       └── mobility/            # School transport operating guidelines
├── research/
│   ├── issue_resolution_workflows.md   # Ground-truth workflow spec
│   └── *.pdf                           # Source scope documents
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.10+
- A `.env` file in the project root with your Gemini API key:

```
GEMINI_API_KEY=your_key_here
```

Get a Gemini API key at [aistudio.google.com](https://aistudio.google.com).

### Install dependencies

```bash
cd school_transport
pip install -r requirements.txt
```

### Run the backend

```bash
cd school_transport
python -m uvicorn backend.main:app --reload --port 8000
```

On first start the server automatically:
- Creates and seeds the SQLite database (`backend/database/school_transport.db`)
- Initialises the ChromaDB vector store from the policy documents in `rag/documents/`

### Open the dashboard

Open `front/index.html` in a browser. The frontend calls `http://localhost:8000/api` — no additional server needed for the frontend.

Check the API is live: `http://localhost:8000/health`
Interactive API docs: `http://localhost:8000/docs`

---

## The 5 Demo Scenarios

Each scenario maps to a real-world event type. Click any scenario card on the **Command Center** tab to run it.

### Scenario 01 — Driver Distraction (ADAS Camera Alert)
**Event:** ADAS cabin camera on bus AU-BUS-105 detects driver DRV-1001 using a mobile phone for >4 seconds.
**Workflow:** Supervisor → Safety → Evidence → Compliance → Incident → Executive
**What happens:**
- Safety Agent flags the unsafe behaviour and severity
- Evidence Agent captures the camera frame and ingests edge telemetry
- Compliance Agent queries ADEK Reg 4.2.1 (no mobile use while driving), checks driver history — finds 4 prior incidents → rules SUSPEND
- Compliance Agent suspends permit in DB, issues AED 800 fine via MCP, syncs to ADEK Gov Portal
- Incident Agent creates a "Driver Distraction" ticket
- Executive Agent pulls live KPIs and generates a C-suite summary

### Scenario 02 — Missing Guardian at Drop-off
**Event:** Route supervisor reports a Grade 2 student's guardian is absent at stop #4 on route AU-102.
**Workflow:** Supervisor → Fleet Monitoring → Compliance → Incident
**What happens:**
- Fleet Agent checks vehicle manifest — confirms guardian absence
- Compliance Agent queries ADEK Reg 14.2 (students under Grade 3 must not be left unattended) — first offence → rules ASSIGN_TRAINING
- Training SLA assigned to driver (5-day deadline), ADEK notified
- Incident Agent creates a "Missing Guardian" ticket and fires an SMS to the parent via MCP

### Scenario 03 — Vehicle Hardware Failure (Pre-Trip Inspection)
**Event:** Pre-trip inspection report: AU-BUS-104 brake pressure sensor failure, GPS offline.
**Workflow:** Supervisor → Evidence → Fleet Monitoring → Route Optimization → Incident
**What happens:**
- Evidence Agent ingests the inspection telemetry
- Fleet Agent grounds AU-BUS-104 immediately in the fleet database
- Route Optimization Agent dispatches standby bus AU-BUS-106, recalculates the route, broadcasts ETA change to parents
- Incident Agent creates a "Vehicle Hardware Failure" maintenance ticket
- Map on Fleet tab updates to show the grounded bus and standby bus route

### Scenario 04 — Executive Compliance Summary
**Event:** Weekly executive briefing request.
**Workflow:** Supervisor → Executive
**What happens:**
- Supervisor routes directly to Executive Agent (no operational pipeline needed)
- Executive Agent calls `mcp_get_executive_metrics` to pull live KPIs: open incidents, critical incidents, fines issued, pending training SLAs, grounded buses, suspended drivers
- Generates a structured C-suite board summary with real numbers from the database

### Scenario 05 — Pre-Departure Driver Ban
**Event:** Pre-departure compliance gate triggers for driver DRV-1045 (Khalid Al Remeithi) before route AU-BUS-105 departs.
**Workflow:** Supervisor → Compliance → Incident
**What happens:**
- Compliance Agent runs a deterministic pre-departure check: permit = Suspended, medical = Expired, training = Pending Refresher
- Driver is immediately banned per ADEK Operator Reg 3.1
- `mcp_find_available_driver` locates a fully compliant replacement driver
- Replacement driver assigned to AU-BUS-105, departure cleared with ~8 min delay
- Fine issued and ADEK Gov Portal synced
- Incident Agent logs a "Pre-Departure Driver Ban" ticket

---

## Custom Event Input

On the Command Center tab, below the scenario cards, there is a free-text input labelled **"Trigger Custom Agent Event"**. Type any natural language event description and the system will route it through the full pipeline.

**Example inputs to try:**

```
Bus AU-BUS-102 driver spotted not wearing seatbelt on Sheikh Zayed Road
```
```
Student Ahmed Al Rashidi not collected at Khalidiyah stop, guardian not responding
```
```
Hydraulic brake failure reported on AU-BUS-103 during pre-trip inspection
```
```
How many open incidents do we have this week and what is the driver compliance rate?
```
```
Road closure on Al Salam Street affecting routes AU-101 and AU-102
```

The Supervisor Agent reads the text, classifies the event type, and routes to the appropriate agents automatically. If the text mentions a vehicle or driver ID it will be extracted and used in the pipeline.

---

## Deduplication

If you run the **same scenario twice without resetting**, the Supervisor Agent detects an existing open incident of the same type for the same vehicle/driver and halts the pipeline immediately. This prevents alert fatigue — you will see a "Duplicate incident detected — halting pipeline" message in the workflow trace.

**To run a scenario again:** click the **Reset Demo State** button (top right of the Command Center tab). This resolves all open agent-created incidents and un-suspends the demo drivers (DRV-1045, DRV-1004, DRV-1015) so all 5 scenarios are ready for a fresh run.

---

## Executive Insights Panel

On the **Executive Insights** tab there is a live query input. This calls `scenario_id=99` (free-text mode) and routes to the Executive Agent.

The executive query auto-runs on page load with:
`"Generate a brief executive compliance summary for the Abu Dhabi school transport fleet"`

You can also ask specific questions like:
- `"How many drivers have pending training SLAs?"`
- `"What is the current fleet inspection status?"`
- `"Show me all critical open incidents"`

---

## How to Add a New Scenario or Input Type

### Adding a new structured scenario (backend)

1. Assign it a `scenario_id` integer (e.g. `5`)
2. In `backend/agents/supervisor.py`, add a branch in the deterministic routing block that sets `next_step` to the first agent in the workflow
3. Add keyword detection if needed in the relevant agents (`_HARDWARE_KEYWORDS`, `_GUARDIAN_KEYWORDS`, etc.)
4. In `front/index.html`, duplicate a scenario card and set `onclick="runScenario(5)"`
5. In `front/app.js`, add a `case 5` to `getEventTag()` and add a fallback history entry to `getFallbackHistory()`

### Adding a new MCP tool

1. Add the tool function to the appropriate file in `backend/mcp/` using the `@mcp.tool(name="mcp_your_tool_name")` decorator
2. Call it from the relevant agent using: `mcp_client.call_tool("mcp_your_tool_name", param1=value1, ...)`
3. To expose it to the LLM, add it to the `tools` list in the agent's `call_gemini(...)` call

### Adding a new agent

1. Create `backend/agents/your_agent.py` with a function `your_agent(state: AgentState) -> dict` that returns `{"conversation_history": [...], "next_step": "next_node_name"}`
2. Register it in `backend/agents/graph.py`: `workflow.add_node("your_agent", your_agent)` and add it to `edges` and `workflow.add_conditional_edges`
3. Route to it from an existing agent by returning `"next_step": "your_agent"`

---

## Database Tables

The SQLite database at `backend/database/school_transport.db` contains:

| Table | Description |
|---|---|
| `drivers` | 20 seeded drivers (DRV-1001..DRV-1020) — name, permit status, medical status, training status, operator |
| `vehicles` | 6 buses (AU-BUS-101..106) — GPS status, inspection status, capacity, current occupancy, lat/lon |
| `incidents` | All agent-created incident tickets — severity, type, description, status, timestamp |
| `fines` | Fines issued by Compliance Agent — driver, vehicle, violation type, amount, authority |
| `training_slas` | Training SLAs assigned by Compliance Agent — driver, deadline, status |
| `students` | Student roster with assigned vehicle and parent link |
| `parents` | Parent contact info (phone used for SMS alerts) |
| `boardings` | Student boarding/alighting events |
| `roadblocks` | Active roadblocks affecting routes |
| `audit_log` | Full conversation history per incident for compliance audit trail |

### Re-seeding the database

Delete the database file and restart the server — it will re-seed automatically:

```bash
rm backend/database/school_transport.db
python -m uvicorn backend.main:app --reload --port 8000
```

The seeder (`backend/database/seed.py`) is idempotent — it checks for existing data before inserting, so restarting without deleting the DB is safe.

---

## API Reference

All endpoints are under `http://localhost:8000/api`. Full interactive docs at `/docs`.

### Agent Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/agents/run_scenario` | Run a scenario through the full agent pipeline |
| `POST` | `/api/agents/reset_demo` | Resolve all open incidents, un-suspend demo drivers |
| `GET` | `/api/agents/recent_runs` | List recent agent flow executions |

**run_scenario request body:**
```json
{
  "scenario_id": 0,
  "event_payload": "ADAS camera alert: driver distraction detected on AU-BUS-105"
}
```
`scenario_id` can be 0–4 for the named scenarios, or `99` for free-text routing.

**Response:**
```json
{
  "success": true,
  "history": [
    {
      "agent": "Supervisor Agent",
      "text": "...",
      "tool": "LangGraph State Router",
      "action": "Routed to Safety Agent"
    }
  ]
}
```

### Fleet Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/fleet/status` | All drivers and vehicles with current status |
| `GET` | `/api/fleet/kpis` | Dashboard KPI numbers (GPS %, inspection %, open incidents) |
| `GET` | `/api/fleet/fines` | All fines issued |
| `GET` | `/api/fleet/slas` | All training SLAs |
| `GET` | `/api/fleet/boardings` | Recent student boarding events |
| `GET` | `/api/fleet/routes` | GeoJSON route paths for the map (Abu Dhabi coordinates) |

### Incident & Policy Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/incidents/` | All incidents, ordered by timestamp |
| `POST` | `/api/incidents/` | Create an incident manually |
| `GET` | `/api/policy/search?q=...` | Full-text RAG search over ADEK policy documents |

---

## MCP Tools Reference

The MCP server runs as a subprocess and exposes 27 tools across 7 categories:

**Compliance & Enforcement**
- `mcp_issue_fine_ticket` — Issue a regulatory fine (driver, vehicle, violation type, amount, authority)
- `mcp_assign_training_sla` — Assign a mandatory training SLA to a driver
- `mcp_update_driver_status` — Update driver permit/medical/training status in DB
- `mcp_sync_permit_status_with_gov` — Sync permit suspension to ADEK Gov Portal
- `mcp_get_executive_metrics` — Fetch live operational KPIs for executive reporting

**Driver Management**
- `mcp_get_driver_info` — Get driver profile and compliance status
- `mcp_find_available_driver` — Find the next available compliant replacement driver
- `mcp_get_driver_incident_history` — Get all prior incidents for a driver

**Fleet Management**
- `mcp_get_vehicle_status` — Get vehicle GPS, inspection, occupancy status
- `mcp_update_inspection_status` — Ground or clear a vehicle (status: grounded/valid/failed)
- `mcp_get_fleet_summary` — Aggregated fleet health metrics

**Evidence & Telemetry**
- `mcp_capture_camera_evidence` — Capture a camera frame and store as evidence
- `mcp_ingest_edge_telemetry` — Ingest IoT/sensor telemetry from vehicle edge devices
- `mcp_get_evidence_record` — Retrieve an evidence record by ID

**Incident Management**
- `mcp_create_incident` — Create a new incident ticket
- `mcp_update_incident_status` — Update incident status (In Progress, Pending Review, Resolved)
- `mcp_get_incident` — Get a specific incident by ID
- `mcp_list_open_incidents` — List all non-resolved incidents

**Route Operations**
- `mcp_calculate_detour` — Calculate an alternate route given a roadblock
- `mcp_update_bus_schedule` — Update a bus's assigned route in the schedule
- `mcp_broadcast_eta_change` — Broadcast updated ETA to parent portal

**Notifications**
- `mcp_send_sms` — Send SMS to a parent or guardian phone number
- `mcp_send_push` — Send push notification to parent portal app

**Policy / RAG**
- `mcp_search_policy` — Semantic search over ADEK regulation documents in ChromaDB

---

## Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — placeholder for future LLM swap
GROQ_API_KEY=
OPENAI_API_KEY=
```

The system will still start without a Gemini key but agents will fall back to deterministic (non-LLM) paths for all decisions.

---

## Workflow Reference

The five canonical workflows are defined in `research/issue_resolution_workflows.md`. Each maps a scenario to an exact agent sequence:

| Workflow | Trigger | Agent Path |
|---|---|---|
| WF1 — Safety Distraction | ADAS camera alert | Supervisor → Safety → Evidence → Compliance → Incident → Executive |
| WF2 — Route Deviation | Road closure / deviation | Supervisor → Route Optimization → end |
| WF3 — Guardian Absent | Missing guardian at drop-off | Supervisor → Fleet Monitoring → Compliance → Incident |
| WF4 — Hardware Failure | Brake/GPS/sensor failure | Supervisor → Evidence → Fleet Monitoring → Route Optimization → Incident |
| WF5 — Duplicate Event | Same event already open | Supervisor → end (halted) |
| WF6 — Executive Query | KPI / summary request | Supervisor → Executive |
| Pre-Departure Gate | Driver compliance check | Supervisor → Compliance → Incident |
