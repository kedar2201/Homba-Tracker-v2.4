import sys
import os
import sqlite3

# Add the project root to the python path
sys.path.append(os.getcwd())

# Force connection to backend DB
db_path = os.path.join(os.getcwd(), 'backend', 'financial_portfolio.db')
print(f"Connecting to: {db_path}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Access columns by name
cursor = conn.cursor()

def seed_data(source_user_id=2, target_user_id=4):
    try:
        print(f"Seeding data from User {source_user_id} to User {target_user_id}...")

        # 1. Clear existing data for target user (guest)
        print("Clearing existing guest data...")
        cursor.execute("DELETE FROM equities WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM mutual_funds WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM nav_history WHERE user_id = ?", (target_user_id,))
        conn.commit()
        
        # 2. Copy EQUITY
        cursor.execute("SELECT * FROM equities WHERE user_id = ?", (source_user_id,))
        equities = cursor.fetchall()
        print(f"Copying {len(equities)} Equity records...")
        
        for eq in equities:
            # Construct INSERT statement dynamically excluding 'id'
            cols = [key for key in eq.keys() if key != 'id' and key != 'user_id']
            placeholders = ', '.join(['?'] * (len(cols) + 1)) # +1 for user_id
            col_names = ', '.join(cols + ['user_id'])
            
            values = [eq[col] for col in cols] + [target_user_id]
            
            cursor.execute(f"INSERT INTO equities ({col_names}) VALUES ({placeholders})", values)

        # 3. Copy MUTUAL FUNDS
        cursor.execute("SELECT * FROM mutual_funds WHERE user_id = ?", (source_user_id,))
        mfs = cursor.fetchall()
        print(f"Copying {len(mfs)} Mutual Fund records...")

        for mf in mfs:
            cols = [key for key in mf.keys() if key != 'id' and key != 'user_id']
            placeholders = ', '.join(['?'] * (len(cols) + 1))
            col_names = ', '.join(cols + ['user_id'])
            
            values = [mf[col] for col in cols] + [target_user_id]
            
            cursor.execute(f"INSERT INTO mutual_funds ({col_names}) VALUES ({placeholders})", values)
            
        # 4. Copy NAV HISTORY
        cursor.execute("SELECT * FROM nav_history WHERE user_id = ?", (source_user_id,))
        history = cursor.fetchall()
        print(f"Copying {len(history)} NAV History records...")

        for hist in history:
            cols = [key for key in hist.keys() if key != 'id' and key != 'user_id']
            placeholders = ', '.join(['?'] * (len(cols) + 1))
            col_names = ', '.join(cols + ['user_id'])
            
            values = [hist[col] for col in cols] + [target_user_id]
            
            cursor.execute(f"INSERT INTO nav_history ({col_names}) VALUES ({placeholders})", values)

        conn.commit()
        print("Success! Guest data seeded.")

    except Exception as e:
        print(f"Error seeding data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Check if we need to adjust IDs based on DB inspection manually or pass as args
    # Defaults: newuser1 (2) -> guest (4)
    seed_data()
