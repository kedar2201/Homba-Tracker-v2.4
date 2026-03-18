import sqlite3
import os

DB_PATH = "financial_portfolio.db"

def fix_depositor_names():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Update records where depositor_name is empty but depositor_code is 'K'
        print("Fixing records with Code='K' and missing Name...")
        cursor.execute("UPDATE mutual_funds SET depositor_name = 'K' WHERE depositor_code = 'K' AND (depositor_name IS NULL OR depositor_name = '')")
        rows_affected = cursor.rowcount
        print(f"Updated {rows_affected} records to have Depositor Name 'K'.")
        
        # Also fix any where depositor_name like 'ICICI%' (scheme name leaked into depositor column)
        # Only if depositor_code is 'K'
        print("Checking for Scheme Names leaked into Depositor Name...")
        cursor.execute("UPDATE mutual_funds SET depositor_name = 'K' WHERE depositor_code = 'K' AND depositor_name LIKE '%FUND%'")
        rows_leaked = cursor.rowcount
        print(f"Fixed {rows_leaked} records with Scheme Names in Depositor column.")

        conn.commit()
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_depositor_names()
