import sqlite3
import json
import uuid
from datetime import datetime
from config import AUDIT_DB_PATH

def init_db():
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            doc_id TEXT,
            step TEXT,
            prompt TEXT,
            response TEXT,
            parsed TEXT,
            status TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_llm_interaction(doc_id: str, step: str, prompt: str, response: str, parsed: dict, status: str):
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO audit_logs (id, doc_id, step, prompt, response, parsed, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (log_id, doc_id, step, prompt, response, json.dumps(parsed) if parsed else "", status, timestamp)
    )
    conn.commit()
    conn.close()

# Initialize immediately when module is imported
init_db()
