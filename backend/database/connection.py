import sqlite3
import os
from ..config import settings

def get_db_connection():
    """Retrieve connection thread-safely with dict-like row output mapping."""
    db_dir = os.path.dirname(settings.SQLITE_DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
