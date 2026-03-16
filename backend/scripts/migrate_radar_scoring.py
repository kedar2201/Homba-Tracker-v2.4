import sqlite3

db_path = 'financial_portfolio.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("PRAGMA table_info(radar_scoring_weights);")
cols = [row[1] for row in c.fetchall()]

missing_columns = {
    'weight_dip': 'INTEGER DEFAULT 12',
    'weight_rsi': 'INTEGER DEFAULT 8',
    'weight_dma': 'INTEGER DEFAULT 12',
    'weight_breakout': 'INTEGER DEFAULT 12',
    'weight_market_bonus': 'INTEGER DEFAULT 6',
    'weight_pe_discount': 'INTEGER DEFAULT 12',
    'weight_peg': 'INTEGER DEFAULT 8',
    'weight_roe': 'INTEGER DEFAULT 10',
    'weight_roce_nim_ev': 'INTEGER DEFAULT 10',
    'weight_quality_3': 'INTEGER DEFAULT 0',
    'weight_risk_pe': 'INTEGER DEFAULT 2',
    'weight_risk_earnings': 'INTEGER DEFAULT 4',
    'weight_risk_debt': 'INTEGER DEFAULT 4',
    'use_dip': 'BOOLEAN DEFAULT 1',
    'use_rsi': 'BOOLEAN DEFAULT 1',
    'use_dma': 'BOOLEAN DEFAULT 1',
    'use_breakout': 'BOOLEAN DEFAULT 1',
    'use_market_bonus': 'BOOLEAN DEFAULT 1',
    'use_pe_discount': 'BOOLEAN DEFAULT 1',
    'use_peg': 'BOOLEAN DEFAULT 1',
    'use_quality': 'BOOLEAN DEFAULT 1',
    'use_risk': 'BOOLEAN DEFAULT 1'
}

for col, dtype in missing_columns.items():
    if col not in cols:
        print(f"Adding column {col} to radar_scoring_weights")
        c.execute(f"ALTER TABLE radar_scoring_weights ADD COLUMN {col} {dtype}")

conn.commit()
conn.close()
print("Migration completed.")
