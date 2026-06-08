import sqlite3
import os
from ..config import settings


def get_db_connection() -> sqlite3.Connection:
    """Open a SQLite connection safe for multi-threaded FastAPI workers.

    - check_same_thread=False: required when FastAPI shares connections
      across async/thread boundaries.
    - WAL journal mode: allows concurrent readers alongside a single writer.
    """
    db_dir = os.path.dirname(settings.SQLITE_DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
