import sqlite3
import os

db_path = "financial_portfolio.db"

def set_admin():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Try to find 'admin' user
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
    if cursor.rowcount > 0:
        print("Updated 'admin' user to is_admin=1")
    else:
        print("'admin' user not found.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    set_admin()
