from sqlalchemy import text, create_engine, inspect
import os

# Database URL
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "financial_portfolio.db")
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL)

def sync_tracklist_full():
    inspector = inspect(engine)
    if 'tracklists' not in inspector.get_table_names():
        print("Table 'tracklists' does not exist yet.")
        return

    columns = [c['name'] for c in inspector.get_columns('tracklists')]
    
    # Model-2Q Data and Weights
    missing_columns = {
        "sector_type": "VARCHAR",
        "roe": "FLOAT",
        "roce": "FLOAT",
        "nim": "FLOAT",
        "gnpa": "FLOAT",
        "ev_growth": "FLOAT",
        "solvency_ratio": "FLOAT",
        "use_custom_weights": "BOOLEAN",
        "weight_dip": "INTEGER",
        "weight_rsi": "INTEGER",
        "weight_dma": "INTEGER",
        "weight_breakout": "INTEGER",
        "weight_market_bonus": "INTEGER",
        "weight_pe_discount": "INTEGER",
        "weight_peg": "INTEGER",
        "weight_roe": "INTEGER",
        "weight_roce_nim_ev": "INTEGER",
        "weight_quality_3": "INTEGER",
        "weight_risk_pe": "INTEGER",
        "weight_risk_earnings": "INTEGER",
        "weight_risk_debt": "INTEGER",
        "use_quality": "BOOLEAN",
        "use_risk": "BOOLEAN"
    }
    
    with engine.connect() as conn:
        for col, col_type in missing_columns.items():
            if col not in columns:
                print(f"Adding missing column to tracklists: {col}")
                try:
                    conn.execute(text(f"ALTER TABLE tracklists ADD COLUMN {col} {col_type}"))
                except Exception as e:
                    print(f"Error adding {col}: {e}")
        conn.commit()
    print("Tracklists table sync complete.")

if __name__ == "__main__":
    sync_tracklist_full()
