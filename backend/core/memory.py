from typing import Dict, Any, List
import uuid
from datetime import datetime
from .database import get_db_connection

# In-memory session store
# Structure:
# {
#   session_id: {
#     "conversation": [{"role": "user", "content": "..."}],
#     "signals": {},
#     "stage": "exploration",
#     "last_active": timestamp
#   }
# }
SESSIONS: Dict[str, Any] = {}

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "conversation": [],
            "signals": {
                "stress": 0,
                "fatigue": 0,
                "low_mood": 0,
                "anxiety": 0,
                "sleep_issues": 0,
                "self_worth": 0,
                "attention": 0
            },
            "stage": "opening",
            "last_active": datetime.now()
        }

    
    # Ensure session exists in DB
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        import json
        cur.execute(
            "INSERT INTO v2_chat_history (id, conversation) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", 
            (session_id, json.dumps([]))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error ensuring session: {e}")

    SESSIONS[session_id]["last_active"] = datetime.now()
    return SESSIONS[session_id]

def update_session(session_id: str, data: Dict[str, Any]):
    if session_id in SESSIONS:
        SESSIONS[session_id].update(data)
        SESSIONS[session_id]["last_active"] = datetime.now()

def clear_session(session_id: str):
    if session_id in SESSIONS:
        del SESSIONS[session_id]

def add_message(session_id: str, role: str, content: str):
    session = get_session(session_id)
    session["conversation"].append({"role": role, "content": content})
    
    # Save to DB (Update JSONB column)
    import json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE v2_chat_history SET conversation = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (json.dumps(session["conversation"]), session_id)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error saving message: {e}")
