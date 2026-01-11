import os
import psycopg2
from dotenv import load_dotenv
from core.database import init_db

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_CONNECTION_STRING")

def fix_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Dropping outdated 'summaries' table...")
        cur.execute("DROP TABLE IF EXISTS summaries;")
        conn.commit()
        cur.close()
        conn.close()
        print("Table dropped.")
        
        print("Re-initializing database...")
        init_db()
        print("Database fixed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_db()
