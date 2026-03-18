import sqlite3
import os

def migrate():
    db_path = os.path.join(os.getcwd(), "financial_portfolio.db")
    if not os.path.exists(db_path):
        # Try parent dir if running from subfolder
        db_path = os.path.join(os.path.dirname(os.getcwd()), "financial_portfolio.db")
    
    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Update equities table
    print("Updating 'equities' table...")
    try:
        cursor.execute("ALTER TABLE equities ADD COLUMN yahoo_symbol VARCHAR(30)")
        print("  Added column 'yahoo_symbol' to 'equities'")
    except sqlite3.OperationalError:
        print("  Column 'yahoo_symbol' already exists in 'equities'")

    try:
        cursor.execute("ALTER TABLE equities ADD COLUMN yahoo_symbol_locked BOOLEAN DEFAULT 0")
        print("  Added column 'yahoo_symbol_locked' to 'equities'")
    except sqlite3.OperationalError:
        print("  Column 'yahoo_symbol_locked' already exists in 'equities'")

    # 2. Update price_cache table
    print("Updating 'price_cache' table...")
    try:
        cursor.execute("ALTER TABLE price_cache ADD COLUMN yahoo_symbol VARCHAR(30)")
        print("  Added column 'yahoo_symbol' to 'price_cache'")
    except sqlite3.OperationalError:
        print("  Column 'yahoo_symbol' already exists in 'price_cache'")

    try:
        cursor.execute("ALTER TABLE price_cache ADD COLUMN yahoo_symbol_locked BOOLEAN DEFAULT 0")
        print("  Added column 'yahoo_symbol_locked' to 'price_cache'")
    except sqlite3.OperationalError:
        print("  Column 'yahoo_symbol_locked' already exists in 'price_cache'")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
