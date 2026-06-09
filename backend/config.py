import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Project root = two levels up from this file (backend/config.py)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from root .env
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


class Settings(BaseSettings):
    PROJECT_NAME: str = "ADEK School Transportation AI Compliance Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # SQLite — runtime data, gitignored
    SQLITE_DB_PATH: str = os.path.join(_PROJECT_ROOT, "backend", "database", "school_transport.db")

    # ChromaDB vector store — runtime data, gitignored
    CHROMA_DB_PATH: str = os.path.join(_PROJECT_ROOT, "backend", "rag", "chroma_db")

    # RAG source documents — versioned in rag/documents/
    RAG_DOCS_PATH: str = os.path.join(_PROJECT_ROOT, "rag", "documents")

    # LLM provider keys (optional — used when swapping in real LLM agents)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        case_sensitive = True


settings = Settings()
