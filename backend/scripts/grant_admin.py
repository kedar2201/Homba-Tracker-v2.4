import sqlite3
import os
import sys

db_path = "financial_portfolio.db"

def set_admin(username):
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    if cursor.rowcount > 0:
        print(f"✅ SUCCESS: User '{username}' is now an ADMIN.")
        # Also ensure they are verified and trial is active
        cursor.execute("UPDATE users SET is_verified = 1, license_status = 'active' WHERE username = ?", (username,))
    else:
        print(f"❌ ERROR: User '{username}' not found.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        set_admin(sys.argv[1])
    else:
        # Default to a few common ones for testing if no arg provided
        set_admin("testuser1")
        set_admin("demo")
