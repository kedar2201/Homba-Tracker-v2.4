
import sqlite3
import os

# Connect to the database
db_path = "financial_portfolio.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column exists
    cursor.execute("PRAGMA table_info(nav_history)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "mf_nav" not in columns:
        print("Adding mf_nav column...")
        cursor.execute("ALTER TABLE nav_history ADD COLUMN mf_nav FLOAT DEFAULT 0")
        conn.commit()
        print("mf_nav column added successfully.")
    else:
        print("mf_nav column already exists.")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
