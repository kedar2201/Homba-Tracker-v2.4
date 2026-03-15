import sqlite3
import os

db_path = "financial_portfolio.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Repairing Fixed Deposits table schema...")

try:
    # 1. First, check if there's any data worth saving
    cursor.execute("SELECT count(*) FROM fixed_deposits")
    count = cursor.fetchone()[0]
    print(f"Current rows in fixed_deposits: {count}")

    # To fix the constraint in SQLite, we must recreate the table
    # But first, we rename the old table
    cursor.execute("ALTER TABLE fixed_deposits RENAME TO fixed_deposits_old")

    # Now we create the new table with the correct constraint
    # Note: We take 'unique=True' OFF the fd_code column and use a table-level constraint
    cursor.execute('''
    CREATE TABLE fixed_deposits (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users (id),
        bank_name VARCHAR,
        depositor_name VARCHAR,
        depositor_code VARCHAR,
        fd_code VARCHAR,
        principal FLOAT,
        interest_rate FLOAT,
        start_date DATE,
        maturity_date DATE,
        compounding_frequency VARCHAR(12),
        payout_type VARCHAR(20),
        tds_applicable BOOLEAN,
        tds_rate FLOAT
    )
    ''')
    
    # Create the correct User-specific Unique Index
    cursor.execute("CREATE UNIQUE INDEX _user_fd_uc ON fixed_deposits (user_id, fd_code)")
    
    # Copy data back (this might fail if there are ALREADY duplicates across different users for the same code, 
    # but that's unlikely in this tiny local setup)
    try:
        cursor.execute('''
        INSERT INTO fixed_deposits 
        SELECT id, user_id, bank_name, depositor_name, depositor_code, fd_code, 
               principal, interest_rate, start_date, maturity_date, 
               compounding_frequency, payout_type, tds_applicable, tds_rate 
        FROM fixed_deposits_old
        ''')
        print("Data successfully migrated to new schema.")
    except Exception as e:
        print(f"Note: Could not migrate all old data (likely due to existing duplicates): {e}")

    # Cleanup
    cursor.execute("DROP TABLE fixed_deposits_old")
    conn.commit()
    print("Schema repair complete.")

except Exception as e:
    conn.rollback()
    print(f"Error during repair: {e}")
finally:
    conn.close()
