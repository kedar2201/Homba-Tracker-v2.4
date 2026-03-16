
from app.database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            # Check if columns exist
            result = conn.execute(text("PRAGMA table_info(price_cache)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "forward_eps" not in columns:
                print("Adding forward_eps column...")
                conn.execute(text("ALTER TABLE price_cache ADD COLUMN forward_eps FLOAT"))
            
            if "earnings_growth" not in columns:
                print("Adding earnings_growth column...")
                conn.execute(text("ALTER TABLE price_cache ADD COLUMN earnings_growth FLOAT"))
                
            print("Migration complete!")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_columns()
