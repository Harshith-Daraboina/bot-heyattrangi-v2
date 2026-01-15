import os
import uuid
import json
from core.database import init_db, get_db_connection
from core.memory import add_message, get_session

# Ensure we are checking the right logic
def test_v2_db():
    print("Initializing V2 DB (Single Table)...")
    init_db()
    
    session_id = str(uuid.uuid4())
    print(f"Testing with Session ID: {session_id}")
    
    # 1. Test Session Creation (Implicit in get_session)
    print("Getting session (should create in DB)...")
    get_session(session_id)
    
    # Verify in DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT conversation FROM v2_chat_history WHERE id = %s", (session_id,))
    row = cur.fetchone()
    if row:
        conversation = row['conversation']
        if isinstance(conversation, str): conversation = json.loads(conversation)
        print(f"✅ Session found in v2_chat_history.")
        if conversation == []:
             print("✅ Initial conversation is empty list")
    else:
        print("❌ Session NOT found in v2_chat_history")
        
    # 2. Test Message Addition
    print("Adding message 'Hello V2 Single Table'...")
    add_message(session_id, "user", "Hello V2 Single Table")
    
    # Verify in DB
    cur.execute("SELECT conversation FROM v2_chat_history WHERE id = %s", (session_id,))
    row = cur.fetchone()
    if row:
        conversation = row['conversation']
        if isinstance(conversation, str): conversation = json.loads(conversation)
        # Should be list with 1 item
        if len(conversation) > 0 and conversation[-1]['content'] == "Hello V2 Single Table":
             print("✅ Message found in conversation JSON")
        else:
             print(f"❌ Message NOT found or mismatch: {conversation}")
    
    # 3. Test Summary Update
    print("Updating summary...")
    cur.execute("UPDATE v2_chat_history SET summary = %s WHERE id = %s", ("V2 Test Summary", session_id))
    conn.commit()
    
    # Verify Summary
    cur.execute("SELECT summary FROM v2_chat_history WHERE id = %s", (session_id,))
    row = cur.fetchone()
    if row and row['summary'] == "V2 Test Summary":
        print("✅ Summary field updated successfully")
    else:
        print(f"❌ Summary update failed: {row}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    test_v2_db()
