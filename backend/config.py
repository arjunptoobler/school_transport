import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ADEK School Transportation AI Compliance Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Databases
    SQLITE_DB_PATH: str = os.path.join(os.path.dirname(__file__), "database", "school_transport.db")
    CHROMA_DB_PATH: str = os.path.join(os.path.dirname(__file__), "rag", "chroma_db")
    
    # LLM Provider Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    class Config:
        case_sensitive = True

settings = Settings()
