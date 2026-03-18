import sqlite3
import os

db_path = "financial_portfolio.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # List of columns to add to tracklists
    # (col_name, type, default)
    columns = [
        ("use_custom_weights", "BOOLEAN", "0"),
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

    for col, ctype, default in columns:
        try:
            print(f"Adding column {col} to tracklists...")
            cur.execute(f"ALTER TABLE tracklists ADD COLUMN {col} {ctype} DEFAULT {default}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col} already exists.")
            else:
                print(f"Error adding {col}: {e}")

    # Also update radar_scoring_weights table
    scoring_columns = [
        ("weight_roe", "INTEGER", "10"),
        ("weight_roce_nim_ev", "INTEGER", "10"),
        ("weight_quality_3", "INTEGER", "0"),
        ("use_quality", "BOOLEAN", "1"),
    ]

    for col, ctype, default in scoring_columns:
        try:
            print(f"Adding column {col} to radar_scoring_weights...")
            cur.execute(f"ALTER TABLE radar_scoring_weights ADD COLUMN {col} {ctype} DEFAULT {default}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col} already exists.")
            else:
                print(f"Error adding {col}: {e}")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
