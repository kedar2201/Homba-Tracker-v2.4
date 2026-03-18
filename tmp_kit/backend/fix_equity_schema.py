import sqlite3
import os

db_path = 'c:/Users/kedar/.gemini/antigravity/scratch/financial_portfolio_tracker/backend/financial_portfolio.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE equities ADD COLUMN instrument_type TEXT')
        conn.commit()
        print("Column 'instrument_type' added successfully to 'equities' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'instrument_type' already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database not found at {db_path}")
