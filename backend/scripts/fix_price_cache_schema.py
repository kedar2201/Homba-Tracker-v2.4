import sqlite3
import os

DB_PATH = "financial_portfolio.db"

def migrate_price_cache():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # List of new columns to add
    new_columns = [
        ("ma50", "REAL"),
        ("ma200", "REAL"),
        ("eps", "REAL"),
        ("pe", "REAL"),
        ("analytics_updated_at", "DATETIME")
    ]

    print("Checking price_cache table schema...")
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(price_cache)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE price_cache ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists.")
                
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_price_cache()
