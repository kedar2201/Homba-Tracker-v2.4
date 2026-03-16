import sqlite3

def fix_numeric_exchanges():
    db_path = 'financial_portfolio.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update numeric symbols to BSE if they are marked as NSE
    # In SQLite, GLOB '[0-9]*' finds items starting with a digit
    cursor.execute("UPDATE equities SET exchange = 'BSE' WHERE symbol GLOB '[0-9]*' AND (exchange = 'NSE' OR exchange IS NULL)")
    print(f"Fixed {cursor.rowcount} numeric symbols to BSE.")
    
    # 2. Update scrip_name if it's currently NULL to be the symbol (initial data migration)
    cursor.execute("UPDATE equities SET scrip_name = symbol WHERE scrip_name IS NULL")
    print(f"Populated {cursor.rowcount} missing scrip_names.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_numeric_exchanges()
