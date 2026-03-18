import sqlite3
import os

DB_PATH = "financial_portfolio.db"
# DB is likely in backend root or app folder, but let's check current dir
if not os.path.exists(DB_PATH):
    # Try looking one level up or down if needed, but for now let's assume it is in CWD if ran from backend
    # Actually, the app logic usually uses 'portfolio.db' in the CWD of main.py
    pass

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Attempting to add 'eps_growth' column to 'price_cache'...")
        cursor.execute("ALTER TABLE price_cache ADD COLUMN eps_growth FLOAT DEFAULT 10.0")
        conn.commit()
        print("Successfully added 'eps_growth' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'eps_growth' already exists.")
        else:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
