"""
Script to seed test data for development.
Usage: python seed_test_data.py [--reset]
"""
import argparse
import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.fixed_deposit import FixedDeposit, CompoundingFrequency, PayoutType
from app.models.equity import Equity, Exchange
from app.models.mutual_fund import MutualFund
from app.auth.auth import get_password_hash

# Ensure we are in backend/ directory for relative paths
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def seed_data(reset=False):
    db = SessionLocal()
    
    if reset:
        print("Resetting database...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    # 1. Create Test Users
    print("Creating test users...")
    users = [
        {"username": "testuser1", "email": "user1@example.com", "password": "password123"},
        {"username": "testuser2", "email": "user2@example.com", "password": "password123"}
    ]
    
    created_users = {}
    for u_data in users:
        existing = db.query(User).filter(User.username == u_data["username"]).first()
        if not existing:
            user = User(
                username=u_data["username"],
                email=u_data["email"],
                hashed_password=get_password_hash(u_data["password"])
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users[user.username] = user
            print(f"Created user: {user.username}")
        else:
            created_users[u_data["username"]] = existing
            print(f"User {u_data['username']} already exists.")

    test_user_id = created_users["testuser1"].id

    # 2. Load Fixed Deposits
    fd_path = "test_data/fd_upload_test.csv"
    if os.path.exists(fd_path):
        print(f"Loading FDs from {fd_path}...")
        df_fd = pd.read_csv(fd_path)
        for _, row in df_fd.iterrows():
            # Check if exists to avoid dupes if not reset
            exists = db.query(FixedDeposit).filter(FixedDeposit.fd_code == str(row["FD_Code"])).first()
            if not exists:
                fd = FixedDeposit(
                    user_id=test_user_id,
                    bank_name=row["Bank_Name"],
                    fd_code=str(row["FD_Code"]),
                    principal=float(row["Principal"]),
                    interest_rate=float(row["Interest_Rate"]),
                    start_date=pd.to_datetime(row["Start_Date"]).date(),
                    maturity_date=pd.to_datetime(row["Maturity_Date"]).date(),
                    compounding_frequency=CompoundingFrequency(row["Compounding_Frequency"]),
                    payout_type=PayoutType(row["Payout_Type"]),
                    tds_applicable=bool(row.get("TDS_Applicable", False)),
                    tds_rate=float(row.get("TDS_Rate", 0.0))
                )
                db.add(fd)
        db.commit()
        print("FDs loaded.")

    # 3. Load Equity
    eq_path = "test_data/equity_upload_test.csv"
    if os.path.exists(eq_path):
        print(f"Loading Equity from {eq_path}...")
        df_eq = pd.read_csv(eq_path)
        for _, row in df_eq.iterrows():
            eq = Equity(
                user_id=test_user_id,
                exchange=Exchange(row["Exchange"]),
                symbol=str(row["Symbol"]),
                quantity=int(row["Quantity"]),
                buy_price=float(row["Buy_Price"]),
                buy_date=pd.to_datetime(row["Buy_Date"]).date(),
                isin=row.get("ISIN", None),
                broker=row.get("Broker", None)
            )
            db.add(eq)
        db.commit()
        print("Equity loaded.")

    # 4. Load Mutual Funds
    mf_path = "test_data/mf_upload_test.csv"
    if os.path.exists(mf_path):
        print(f"Loading MFs from {mf_path}...")
        df_mf = pd.read_csv(mf_path)
        for _, row in df_mf.iterrows():
            mf = MutualFund(
                user_id=test_user_id,
                scheme_name=row["Scheme_Name"],
                isin=str(row["ISIN"]),
                units=float(row["Units"]),
                invested_amount=float(row["Invested_Amount"]),
                transaction_date=pd.to_datetime(row["Transaction_Date"]).date(),
                amc_name=row.get("AMC_Name", None)
            )
            db.add(mf)
        db.commit()
        print("Mutual Funds loaded.")

    db.close()
    print("Test data seeding complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    args = parser.parse_args()
    
    # Check enviroment variable as a safety
    if os.getenv("USE_TEST_DATA", "false").lower() != "true":
        print("WARNING: USE_TEST_DATA environment variable is not set to 'true'.")
        print("For safety, this script will exit. Set USE_TEST_DATA=true to run.")
        sys.exit(1)

    seed_data(args.reset)
