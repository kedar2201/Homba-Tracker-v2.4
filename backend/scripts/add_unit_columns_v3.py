import sys
import os
from sqlalchemy import create_engine, text

# Add parent dir to path to import app modules if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SQLALCHEMY_DATABASE_URL as DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Starting Unitization Migration...")
        
        # 1. Add Columns to Equities
        # Check if column exists first to avoid error
        try:
            conn.execute(text("ALTER TABLE equities ADD COLUMN buy_units FLOAT DEFAULT 0"))
            print("Added buy_units to equities")
        except Exception as e:
            print(f"buy_units might already exist in equities: {e}")

        try:
            conn.execute(text("ALTER TABLE equities ADD COLUMN sell_units FLOAT DEFAULT 0"))
            print("Added sell_units to equities")
        except Exception as e:
            print(f"sell_units might already exist in equities: {e}")

        # 2. Add Columns to Mutual Funds
        # Note: 'units' column exists in MF for *quantity*. We use 'p_buy_units' (Portfolio Units).
        try:
            conn.execute(text("ALTER TABLE mutual_funds ADD COLUMN p_buy_units FLOAT DEFAULT 0"))
            print("Added p_buy_units to mutual_funds")
        except Exception as e:
            print(f"p_buy_units might already exist in mutual_funds: {e}")

        try:
            conn.execute(text("ALTER TABLE mutual_funds ADD COLUMN p_sell_units FLOAT DEFAULT 0"))
            print("Added p_sell_units to mutual_funds")
        except Exception as e:
            print(f"p_sell_units might already exist in mutual_funds: {e}")

        conn.commit()
        
        # 3. Backfill Data (NAV = 100)
        print("Backfilling Equities...")
        # For ACTIVE: buy_units = (buy_price * quantity) / 100
        # For SOLD: buy_units = (buy_price * quantity) / 100 AND sell_units = (sell_price * quantity) / 100
        # NOTE: Logic assumes *historical* NAV was 100. This is the baseline reset.
        
        # In SQLite, we can do this with update queries
        conn.execute(text("""
            UPDATE equities 
            SET buy_units = (buy_price * quantity) / 100.0
            WHERE buy_units IS NULL OR buy_units = 0
        """))
        
        conn.execute(text("""
            UPDATE equities 
            SET sell_units = (sell_price * quantity) / 100.0
            WHERE status = 'SOLD' AND (sell_units IS NULL OR sell_units = 0)
        """))
        
        print("Backfilling Mutual Funds...")
        # MF 'invested_amount' is reliable? Or 'avg_price' * 'units'?
        # MF Model has: units, avg_price, invested_amount. 
        # Safest is avg_price * units if invested_amount is missing, but invested_amount is ideal.
        # Fallback to invested_amount / 100.
        
        conn.execute(text("""
            UPDATE mutual_funds 
            SET p_buy_units = invested_amount / 100.0
            WHERE p_buy_units IS NULL OR p_buy_units = 0
        """))
        
        conn.execute(text("""
            UPDATE mutual_funds 
            SET p_sell_units = (units * sell_nav) / 100.0
            WHERE status = 'SOLD' AND (p_sell_units IS NULL OR p_sell_units = 0)
        """))
        
        conn.commit()
        print("Migration and Backfill Complete.")

if __name__ == "__main__":
    migrate()
