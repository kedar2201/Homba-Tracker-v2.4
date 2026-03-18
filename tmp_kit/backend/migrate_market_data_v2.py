import sqlite3
import os

db_path = "financial_portfolio.db"
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns = [
    ("pe_avg_5y", "FLOAT"),
    ("peg_ratio", "FLOAT")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE price_cache ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError:
        print(f"Column {col_name} already exists or error")

conn.commit()
conn.close()
print("Migration complete")
