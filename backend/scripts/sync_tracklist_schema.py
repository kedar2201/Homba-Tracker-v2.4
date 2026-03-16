import sys
import os
import sqlite3

# Set up paths to import app
sys.path.append(os.getcwd())

from app.database import Base, engine
from app.models.user import Tracklist

def sync_schema():
    conn = sqlite3.connect("financial_portfolio.db")
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(tracklists)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    # Required columns for Tracklist
    required_cols = [
        ("use_custom_weights", "BOOLEAN", "0"),
        ("weight_dip", "INTEGER", "0"),
        ("weight_rsi", "INTEGER", "0"),
        ("weight_dma", "INTEGER", "0"),
        ("weight_breakout", "INTEGER", "0"),
        ("weight_market_bonus", "INTEGER", "0"),
        ("weight_pe_discount", "INTEGER", "0"),
        ("weight_peg", "INTEGER", "0"),
        ("use_dip", "BOOLEAN", "1"),
        ("use_rsi", "BOOLEAN", "1"),
        ("use_dma", "BOOLEAN", "1"),
        ("use_breakout", "BOOLEAN", "1"),
        ("use_market_bonus", "BOOLEAN", "1"),
        ("use_pe_discount", "BOOLEAN", "1"),
        ("use_peg", "BOOLEAN", "1"),
        ("sector_type", "TEXT", "'standard'"),
        ("roe", "REAL", "0.0"),
        ("roce", "REAL", "0.0"),
        ("nim", "REAL", "0.0"),
        ("gnpa", "REAL", "0.0"),
        ("ev_growth", "REAL", "0.0"),
        ("solvency_ratio", "REAL", "0.0"),
        ("weight_roe", "INTEGER", "0"),
        ("weight_roce_nim_ev", "INTEGER", "0"),
        ("weight_quality_3", "INTEGER", "0"),
        ("use_quality", "BOOLEAN", "1"),
        ("weight_risk_pe", "INTEGER", "0"),
        ("weight_risk_earnings", "INTEGER", "0"),
        ("weight_risk_debt", "INTEGER", "0"),
        ("use_risk", "BOOLEAN", "1"),
        ("last_alert_score", "INTEGER", "0"),
    ]
    
    for col, ctype, default in required_cols:
        if col not in existing_cols:
            print(f"Adding missing column: {col}")
            try:
                cursor.execute(f"ALTER TABLE tracklists ADD COLUMN {col} {ctype} DEFAULT {default}")
            except Exception as e:
                print(f"Error adding {col}: {e}")
                
    conn.commit()
    conn.close()
    print("Schema sync complete.")

if __name__ == "__main__":
    sync_schema()
