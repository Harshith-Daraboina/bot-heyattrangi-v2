import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_CONNECTION_STRING")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'summaries';")
    rows = cur.fetchall()
    print("Columns in 'summaries' table:", [r[0] for r in rows])
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
