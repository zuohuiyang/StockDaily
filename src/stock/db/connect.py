import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

