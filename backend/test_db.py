from app.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print(f"DB Success: {res.fetchone()}")
except Exception as e:
    print(f"DB Failed: {e}")
