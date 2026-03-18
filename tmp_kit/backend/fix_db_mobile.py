import sqlite3
import os

# Use relative path so it works on production server too
db_path = os.path.join(os.path.dirname(__file__), "financial_portfolio.db")

def fix_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Add mobile_number to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN mobile_number TEXT;")
        print("Added mobile_number column to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("mobile_number column already exists.")
        else:
            print(f"Error adding mobile_number: {e}")

    # 2. Add is_active to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1;")
        print("Added is_active column to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("is_active column already exists.")
        else:
            print(f"Error adding is_active: {e}")

    # 3. Add email to users table if missing (sometimes it is)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT;")
        print("Added email column to users table.")
    except sqlite3.OperationalError: pass

    # 3b. Add radar_mode to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN radar_mode TEXT DEFAULT 'balanced';")
        print("Added radar_mode column to users table.")
    except sqlite3.OperationalError: pass

    # 3c. Add extension_count to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN extension_count INTEGER DEFAULT 0;")
        print("Added extension_count column to users table.")
    except sqlite3.OperationalError: pass

    # 4. Create notifications table if missing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT,
        is_read BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 4. Create alert_settings table if missing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        stock_drop_pct FLOAT DEFAULT 5.0,
        portfolio_drop_pct FLOAT DEFAULT 3.0,
        nifty_drop_pct FLOAT DEFAULT 2.0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 5. Create tracklists table if missing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        symbol TEXT,
        target_price FLOAT,
        dma50_condition TEXT DEFAULT 'IGNORE',
        dma200_condition TEXT DEFAULT 'IGNORE',
        dip_percent FLOAT DEFAULT 8.0,
        rsi_threshold FLOAT DEFAULT 38.0,
        near_50dma_percent FLOAT DEFAULT 2.0,
        near_200dma_percent FLOAT DEFAULT 3.0,
        breakout_enabled BOOLEAN DEFAULT 1,
        min_confidence_score INTEGER DEFAULT 60,
        alert_mode TEXT DEFAULT 'digest',
        last_alert_score INTEGER DEFAULT 0,
        last_triggered_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 5b. Add new columns to tracklists if missing
    new_tracklist_cols = [
        ("dma50_condition", "TEXT DEFAULT 'IGNORE'"),
        ("dma200_condition", "TEXT DEFAULT 'IGNORE'"),
        ("dip_percent", "FLOAT DEFAULT 8.0"),
        ("rsi_threshold", "FLOAT DEFAULT 38.0"),
        ("near_50dma_percent", "FLOAT DEFAULT 2.0"),
        ("near_200dma_percent", "FLOAT DEFAULT 3.0"),
        ("breakout_enabled", "BOOLEAN DEFAULT 1"),
        ("min_confidence_score", "INTEGER DEFAULT 60"),
        ("alert_mode", "TEXT DEFAULT 'digest'"),
        ("last_alert_score", "INTEGER DEFAULT 0"),
        ("trigger_dip", "BOOLEAN DEFAULT 1"),
        ("trigger_rsi", "BOOLEAN DEFAULT 1"),
        ("trigger_dma", "BOOLEAN DEFAULT 1"),
        ("trigger_breakout", "BOOLEAN DEFAULT 1"),
        ("trigger_score", "BOOLEAN DEFAULT 1")
    ]
    for col, definition in new_tracklist_cols:
        try:
            cursor.execute(f"ALTER TABLE tracklists ADD COLUMN {col} {definition};")
            print(f"Added {col} column to tracklists.")
        except sqlite3.OperationalError: pass

    # New columns for price_cache (Model 2 Fundamentals)
    new_price_cols = [
        ("pe_avg_5y", "FLOAT"),
        ("peg_ratio", "FLOAT"),
        ("eps_yoy_growth", "FLOAT"),
        ("debt_yoy_growth", "FLOAT"),
        ("nifty_sma_5d", "FLOAT")
    ]
    for col, definition in new_price_cols:
        try:
            cursor.execute(f"ALTER TABLE price_cache ADD COLUMN {col} {definition}")
            print(f"Added {col} column to price_cache.")
        except sqlite3.OperationalError:
            pass

    # 6. Create radar_signal_log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radar_signal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        symbol TEXT,
        confidence_score INTEGER,
        signal_summary TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 7. Update PriceCache table
    price_cache_cols = [
        ("high_30d", "FLOAT"),
        ("high_3m", "FLOAT"),
        ("avg_vol_20d", "FLOAT"),
        ("current_vol", "FLOAT"),
        ("rsi", "FLOAT")
    ]
    for col, definition in price_cache_cols:
        try:
            cursor.execute(f"ALTER TABLE price_cache ADD COLUMN {col} {definition};")
            print(f"Added {col} column to price_cache.")
        except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    fix_db()
