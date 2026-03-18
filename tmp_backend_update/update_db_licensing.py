import sqlite3
import os

db_path = "financial_portfolio.db"

def update_db():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns_to_add = [
        ("full_name", "TEXT"),
        ("city", "TEXT"),
        ("country", "TEXT"),
        ("device_fingerprint", "TEXT"),
        ("is_verified", "BOOLEAN DEFAULT 0"),
        ("otp_code", "TEXT"),
        ("otp_expiry", "DATETIME"),
        ("license_status", "TEXT DEFAULT 'trial'"),
        ("trial_start_at", "DATETIME"),
        ("trial_end_at", "DATETIME"),
        ("activation_code", "TEXT"),
        ("is_admin", "BOOLEAN DEFAULT 0")
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    update_db()
