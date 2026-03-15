
import sqlite3
import os
db_path = 'C:/apps/portfolio/backend/financial_portfolio.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("PRAGMA table_info(tracklists)")
    cols = [col[1] for col in c.fetchall()]
    if 'yahoo_symbol' not in cols:
        c.execute('ALTER TABLE tracklists ADD COLUMN yahoo_symbol TEXT')
        c.execute('ALTER TABLE tracklists ADD COLUMN yahoo_symbol_locked BOOLEAN DEFAULT 0')
    
    # Add other missing Model-2Q columns if not present
    new_cols = [
        ("sector_type", "TEXT DEFAULT 'standard'"), ("roe", "FLOAT DEFAULT 0.0"), 
        ("roce", "FLOAT DEFAULT 0.0"), ("nim", "FLOAT DEFAULT 0.0"), 
        ("gnpa", "FLOAT DEFAULT 0.0"), ("ev_growth", "FLOAT DEFAULT 0.0"), 
        ("solvency_ratio", "FLOAT DEFAULT 0.0")
    ]
    for col_name, col_def in new_cols:
        if col_name not in cols:
            c.execute(f"ALTER TABLE tracklists ADD COLUMN {col_name} {col_def}")
            
    conn.commit()
    conn.close()
    print('Migration Done')
