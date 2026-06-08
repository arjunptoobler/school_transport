# ADEK School Transportation AI Compliance Platform

Enterprise Agentic AI platform for monitoring, enforcing, and reporting Abu Dhabi school transport compliance using LangGraph multi-agent orchestration, MCP tool servers, and ChromaDB vector RAG.

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
│   │   ├── state.py     # AgentState TypedDict
│   │   ├── supervisor.py
│   │   ├── compliance.py
│   │   ├── safety.py
│   │   ├── incident.py
│   │   └── executive.py
│   ├── mcp/             # Model Context Protocol tool registry
│   │   ├── base.py      # MCPToolRegistry decorator pattern
│   │   ├── policy.py    # RAG policy lookup tools
│   │   ├── fleet.py     # Vehicle status + grounding tools
│   │   ├── driver.py    # Driver permit + training tools
│   │   ├── notification.py  # SMS / Push dispatch tools
│   │   └── incident.py  # Incident create + query tools
│   ├── rag/
│   │   └── vector_db.py # ChromaDB init + query (persistent at backend/rag/chroma_db/)
│   ├── database/
│   │   ├── connection.py  # SQLite thread-safe connection
│   │   ├── models.py      # Pydantic schemas
│   │   └── seed.py        # Idempotent seed (500 drivers, 250 vehicles, 5000 students)
│   └── routes/
│       ├── fleet.py
│       ├── incidents.py
│       ├── policy.py
│       └── agents.py
├── research/            # Source PDFs and reference documents
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

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The server auto-seeds the SQLite database and initialises the ChromaDB vector index on first run. Subsequent restarts skip seeding (idempotent).

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

Drop any ADEK / Abu Dhabi Mobility PDF into `research/`. Then update `backend/rag/vector_db.py` → `init_vector_db()` to parse and chunk the document into `collection.add()` calls. The vector DB will be auto-initialised on next server start.

---

## Scaling to Production

### Replace Mock Embeddings
The current `SimpleCharEmbedding` is a character-frequency baseline sufficient for demo. Replace with:
```python
# Option A: OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
embedding_function = OpenAIEmbeddingFunction(api_key=settings.OPENAI_API_KEY)

# Option B: Local (sentence-transformers)
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
```

### Replace SQLite with PostgreSQL
Update `backend/database/connection.py` to use `psycopg2` or `SQLAlchemy` with a `DATABASE_URL` from `config.py`. All query logic in `routes/` stays the same.

### Add Real LLM to Agents
Each agent node in `backend/agents/` currently uses deterministic logic for demo reliability. To add real LLM reasoning, pass `mcp_registry` tools into a LangChain `AgentExecutor` or LangGraph `ToolNode`:
```python
# In any agent node:
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama3-70b-8192", api_key=settings.GROQ_API_KEY)
```

### Horizontal Scaling
- Run multiple uvicorn workers: `uvicorn backend.main:app --workers 4`
- The agent graph singleton is per-process safe (compiled once on startup)
- Move ChromaDB to a dedicated Chroma server (`chromadb.HttpClient`) for multi-process consistency
- Use Redis for notification queuing instead of the sync `send_sms` mock

### MCP Servers (Production)
The `backend/mcp/` registry simulates MCP tool calls in-process. For production, each tool module can be exposed as a standalone MCP server over stdio or SSE transport using the official `mcp` Python SDK, and called remotely by agents.

### Environment Variables
```bash
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key
SQLITE_DB_PATH=/data/school_transport.db   # override default
CHROMA_DB_PATH=/data/chroma_db             # override default
```
