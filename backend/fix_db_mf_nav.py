import sqlite3
import os
import sys

# Assume we are running from project root
db_path = os.path.join(os.getcwd(), 'backend', 'financial_portfolio.db')

if not os.path.exists(db_path):
    print(f"Database not found at: {db_path}")
    # Fallback check
    if os.path.exists("financial_portfolio.db"):
        db_path = "financial_portfolio.db"
        print(f"Found database in current directory: {db_path}")

print(f"Connecting to database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 1. Check if column exists
    cursor.execute("PRAGMA table_info(nav_history)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'mf_nav' not in columns:
        print("Adding missing column 'mf_nav'...")
        cursor.execute("ALTER TABLE nav_history ADD COLUMN mf_nav FLOAT DEFAULT 0.0")
        print("Column added successfully.")
    else:
        print("Column 'mf_nav' already exists.")

    # 2. Clear potentially corrupted data (safer than trying to fix types in-place)
    print("Clearing nav_history table to remove corrupted data...")
    cursor.execute("DELETE FROM nav_history")
    rows_deleted = cursor.rowcount
    print(f"Deleted {rows_deleted} rows.")

    conn.commit()
    print("\nDatabase Schema Updated and Cleaned Successfully.")
    print("Next Step: Run 'python backfill_nav_history.py' to repopulate data.")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
