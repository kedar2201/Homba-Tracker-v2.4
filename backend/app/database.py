from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Allow overriding via environment variable, but default to a local file for dev if Postgres not set
# Use an absolute path based on the script location to ensure we always hit the same file
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, "financial_portfolio.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")

# If using Postgres, use psycopg2
if SQLALCHEMY_DATABASE_URL.startswith("postgres"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # SQLite specific args
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
