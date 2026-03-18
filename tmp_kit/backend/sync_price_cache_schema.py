from sqlalchemy import text, create_engine, inspect
import os

# Database URL
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "financial_portfolio.db")
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL)

def sync_price_cache_schema():
    inspector = inspect(engine)
    if 'price_cache' not in inspector.get_table_names():
        print("Table 'price_cache' does not exist yet.")
        return

    columns = [c['name'] for c in inspector.get_columns('price_cache')]
    
    missing_columns = {
        "roe": "FLOAT",
        "roce": "FLOAT",
        "ebit_margin": "FLOAT",
        "net_profit_margin": "FLOAT",
        "nim": "FLOAT",
        "gnpa": "FLOAT",
        "solvency_ratio": "FLOAT",
        "ev_growth": "FLOAT"
    }
    
    with engine.connect() as conn:
        for col, col_type in missing_columns.items():
            if col not in columns:
                print(f"Adding missing column: {col}")
                try:
                    conn.execute(text(f"ALTER TABLE price_cache ADD COLUMN {col} {col_type}"))
                except Exception as e:
                    print(f"Error adding {col}: {e}")
        conn.commit()
    print("Price cache schema sync complete.")

if __name__ == "__main__":
    sync_price_cache_schema()
