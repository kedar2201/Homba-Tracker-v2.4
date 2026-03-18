from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Migrating equities...")
        try:
            conn.execute(text("ALTER TABLE equities ADD COLUMN status VARCHAR(10) DEFAULT 'ACTIVE' NOT NULL"))
            print("Added status to equities")
        except Exception as e:
            print(f"Error adding status to equities: {e}")
            
        try:
            conn.execute(text("ALTER TABLE equities ADD COLUMN sell_price FLOAT"))
            print("Added sell_price to equities")
        except Exception as e:
            print(f"Error adding sell_price to equities: {e}")
            
        try:
            conn.execute(text("ALTER TABLE equities ADD COLUMN sell_date DATE"))
            print("Added sell_date to equities")
        except Exception as e:
            print(f"Error adding sell_date to equities: {e}")

        print("\nMigrating mutual_funds...")
        try:
            conn.execute(text("ALTER TABLE mutual_funds ADD COLUMN status VARCHAR(10) DEFAULT 'ACTIVE' NOT NULL"))
            print("Added status to mutual_funds")
        except Exception as e:
            print(f"Error adding status to mutual_funds: {e}")
            
        try:
            conn.execute(text("ALTER TABLE mutual_funds ADD COLUMN sell_nav FLOAT"))
            print("Added sell_nav to mutual_funds")
        except Exception as e:
            print(f"Error adding sell_nav to mutual_funds: {e}")
            
        try:
            conn.execute(text("ALTER TABLE mutual_funds ADD COLUMN sell_date DATE"))
            print("Added sell_date to mutual_funds")
        except Exception as e:
            print(f"Error adding sell_date to mutual_funds: {e}")
            
        conn.commit()
        print("\nMigration complete.")

if __name__ == "__main__":
    migrate()
