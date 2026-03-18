import sqlite3
import os

def check_units(db_path, user_id):
    if not os.path.exists(db_path):
        return f"File not found: {db_path}"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(buy_units) FROM equities WHERE user_id = ?", (user_id,))
        res_eq = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(p_buy_units) FROM mutual_funds WHERE user_id = ?", (user_id,))
        res_mf = cursor.fetchone()[0] or 0
        conn.close()
        return {"equity_units": res_eq, "mf_units": res_mf}
    except Exception as e:
        return f"Error: {e}"

for uid in [1, 2]:
    print(f"\nUSER {uid}:")
    curr = check_units("financial_portfolio.db", uid)
    back = check_units("financial_portfolio_backup.db", uid)
    print(f"  Current: {curr}")
    print(f"  Backup:  {back}")
