# ADEK School Transportation AI Compliance Platform

Enterprise Agentic AI platform for monitoring, enforcing, and reporting Abu Dhabi school transport compliance using LangGraph multi-agent orchestration, Model Context Protocol (MCP) tool integration, and ChromaDB vector RAG.

---

## Project Structure

```
school_transport/
├── front/               # Static dashboard (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── backend/
│   ├── main.py          # FastAPI entrypoint + lifespan (auto seeds DB + RAG)
│   ├── config.py        # Centralized settings via pydantic-settings
│   ├── agents/          # LangGraph multi-agent graph
│   │   ├── graph.py     # Lazy-compiled StateGraph singleton
│   │   ├── state.py     # AgentState with standard operator.add list reducer
│   │   ├── llm.py       # Gemini API client wrapper with fallback
│   │   ├── supervisor.py# Routing supervisor (dynamic LLM routing + fallback)
│   │   ├── compliance.py
│   │   ├── safety.py
│   │   ├── incident.py
│   │   └── executive.py
│   ├── mcp/             # Model Context Protocol tool registry (leak-proof)
│   │   ├── base.py      # MCPToolRegistry decorator pattern
│   │   ├── policy.py    # RAG policy lookup tools
│   │   ├── fleet.py     # Vehicle status + grounding tools
│   │   ├── driver.py    # Driver permit + training tools
│   │   ├── notification.py  # SMS / Push dispatch tools
│   │   └── incident.py  # Incident create + query tools
│   ├── rag/
│   │   ├── vector_db.py # Thread-safe singleton ChromaDB client
│   │   ├── ingestion.py # Walks rag/documents/ directory tree
│   │   └── documents/   # RAG source policy PDFs/text (segregated from research/)
│   │       ├── adek/
│   │       └── mobility/
│   ├── database/
│   │   ├── connection.py  # Thread-safe SQLite connection with WAL mode
│   │   ├── models.py      # Pydantic schemas
│   │   └── seed.py        # Idempotent seed (500 drivers, 250 vehicles, 5000 students)
│   └── routes/
│       ├── fleet.py
│       ├── incidents.py
│       ├── policy.py
│       └── agents.py
├── research/            # Research summaries and architectural reviews
├── requirements.txt
└── README.md
```

---

## Running the Demo

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API backend

To run in real AI-driven mode, supply your Gemini API key. You can do this by creating a `.env` file in the root directory:
```env
GEMINI_API_KEY="AIzaSy..."
```
Or by exporting it in your shell:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
*Note: If `GEMINI_API_KEY` is not supplied, the platform automatically falls back to local database-driven dynamic context outputs (offline demo mode) without crashing.*

The server auto-seeds the SQLite database and initialises the ChromaDB vector index on startup. Subsequent restarts skip seeding (idempotent).

### 3. Start the frontend

```bash
python3 -m http.server 8080 -d front
```

Open **http://localhost:8080** in your browser.

### 4. Demo Scenarios (AI Agents tab)

| # | Scenario | Agents Triggered |
|---|---|---|
| 0 | Driver Mobile Phone Usage | Supervisor → Safety → Compliance → Incident → Executive |
| 1 | Missing Guardian at Drop-off | Supervisor → Safety → Compliance → Incident |
| 2 | Failed Pre-trip Inspection | Supervisor → Compliance → Incident |
| 3 | Weekly Compliance Report | Supervisor → Compliance → Incident → Executive |

### 5. API Documentation

FastAPI auto-generates interactive docs at:
- **http://localhost:8000/docs** (Swagger UI)
- **http://localhost:8000/redoc** (ReDoc)

### 6. Adding PDF Knowledge Base

To add documents to the RAG vector store, drop text or PDFs into the specific subdirectories under `rag/documents/` (e.g., `adek/` or `mobility/`). The vector DB walks this folder tree, slices inputs into batches of 50 to avoid API limits, and auto-ingests new documents on the next server startup. Do not drop RAG source files into `research/` (which is reserved for general research reports and reviews).

---

## Production & Architectural Safeguards

### Standard LangGraph Reducer
`AgentState` is defined using Python's standard `Annotated` reducer type:
```python
conversation_history: Annotated[List[Dict[str, str]], operator.add]
```
Agent nodes return only their incremental updates rather than manually mutating and replacing the state dictionary, eliminating race conditions.

### Dependency-Free REST Client Layer
The LLM and vector RAG clients use direct **HTTP REST requests** to communicate with Google's Gemini API endpoints (`models/gemini-2.5-flash` and `models/gemini-embedding-2`), generating 3072-dimensional vectors. This bypasses the official `google-generativeai` python package to completely eliminate protobuf compatibility issues (`float_precision` errors) and handles 429/503 network rate limits gracefully with immediate fallback.

### Thread-Safe SQLite WAL Mode
The database connection pool is configured with `check_same_thread=False` and runs under **Write-Ahead Logging (WAL)** mode. This enables concurrent readers to access analytics data alongside active agent database write transactions.

### Persistent RAG Singleton client
The ChromaDB persistent client is cached globally inside a thread-safe singleton, avoiding I/O file handle leaks and minimizing latency on vector searches.

### Graceful Connection Auditing
All endpoints, agent nodes, and MCP tools wrap database connections inside `try...finally` blocks to guarantee active SQLite connections are closed immediately upon failure, preventing memory leaks.

