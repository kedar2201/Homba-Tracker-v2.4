import random
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User, Equity, FixedDeposit, MutualFund, OtherAsset, NAVHistory
from app.auth.auth import get_password_hash
from app.models.equity import Exchange, EquityStatus
from app.models.mutual_fund import MFStatus

from app.models.fixed_deposit import FixedDeposit, CompoundingFrequency, PayoutType
from app.models.other_asset import OtherAsset, AssetCategory

def populate_demo():
    db = SessionLocal()
    try:
        # 1. Create Demo User
        demo_user = db.query(User).filter(User.username == "demo").first()
        if not demo_user:
            demo_user = User(
                username="demo",
                email="demo@example.com",
                hashed_password=get_password_hash("demo123")
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            print("Created demo user.")
        else:
            # Clean existing demo data to avoid duplicates
            db.query(Equity).filter(Equity.user_id == demo_user.id).delete()
            db.query(FixedDeposit).filter(FixedDeposit.user_id == demo_user.id).delete()
            db.query(MutualFund).filter(MutualFund.user_id == demo_user.id).delete()
            db.query(OtherAsset).filter(OtherAsset.user_id == demo_user.id).delete()
            db.query(NAVHistory).filter(NAVHistory.user_id == demo_user.id).delete()
            db.commit()
            print("Cleared existing demo data.")

        holders = ["Kedar", "Sneha", "Mahesh", "Huma"]
        
        # 2. Add Equities
        stocks = [
            ("RELIANCE", "Reliance Industries", 2500, 2980),
            ("TCS", "Tata Consultancy Services", 3500, 3950),
            ("HDFCBANK", "HDFC Bank", 1450, 1680),
            ("INFY", "Infosys", 1400, 1620),
            ("ICICIBANK", "ICICI Bank", 950, 1080),
            ("ITC", "ITC Limited", 400, 480),
            ("SBIN", "State Bank of India", 600, 780),
            ("BHARTIARTL", "Bharti Airtel", 1100, 1280),
            ("ADANIENT", "Adani Enterprises", 2800, 3150),
            ("TATAMOTORS", "Tata Motors", 850, 990)
        ]
        
        for symbol, name, buy, current in stocks:
            qty = random.randint(10, 500)
            status = EquityStatus.ACTIVE
            db.add(Equity(
                user_id=demo_user.id,
                exchange=Exchange.NSE,
                symbol=symbol,
                scrip_name=name,
                holder=random.choice(holders),
                quantity=qty,
                buy_price=buy,
                current_price=current,
                buy_date=date.today() - timedelta(days=random.randint(100, 500)),
                status=status
            ))

        # 3. Add FDs
        banks = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra"]
        for i in range(5):
            principal = random.randint(100000, 1000000)
            start = date.today() - timedelta(days=random.randint(30, 365))
            holder = random.choice(holders)
            db.add(FixedDeposit(
                user_id=demo_user.id,
                bank_name=random.choice(banks),
                depositor_name=holder,
                depositor_code=f"DEP-{random.randint(1000, 9999)}",
                fd_code=f"FD-{random.randint(100000, 999999)}",
                principal=principal,
                interest_rate=random.uniform(6.5, 7.8),
                start_date=start,
                maturity_date=start + timedelta(days=365*random.randint(1, 3)),
                compounding_frequency=CompoundingFrequency.QUARTERLY,
                payout_type=PayoutType.CUMULATIVE
            ))

        # 4. Add Mutual Funds
        mfs = [
            ("Axis Bluechip Fund - Direct Plan - Growth", "120465"),
            ("SBI Small Cap Fund - Direct Plan - Growth", "125497"),
            ("Mirae Asset Large Cap Fund - Direct Plan - Growth", "119062"),
            ("HDFC Top 100 Fund - Direct Plan - Growth", "119028"),
            ("ICICI Prudential Bluechip Fund - Direct Plan - Growth", "120166")
        ]
        
        for scheme, amfi in mfs:
            invested = random.randint(50000, 500000)
            holder = random.choice(holders)
            db.add(MutualFund(
                user_id=demo_user.id,
                scheme_name=scheme,
                depositor_name=holder,
                depositor_code=f"MF-{random.randint(1000, 9999)}",
                holder=holder,
                amfi_code=amfi,
                isin=f"INF{random.randint(100000, 999999)}",
                invested_amount=invested,
                units=random.randint(500, 5000),
                transaction_date=date.today() - timedelta(days=random.randint(100, 700)),
                status=MFStatus.ACTIVE
            ))


        # 5. Add Other Assets
        assets = [
            ("Real Estate @ Matunga", 5000000, AssetCategory.REAL_ESTATE),
            ("PPF Kedar", 800000, AssetCategory.RETIREMENT),
            ("Gold @ Safe", 1500000, AssetCategory.GOLD)
        ]
        for name, valuation, category in assets:
            db.add(OtherAsset(
                user_id=demo_user.id,
                name=name,
                valuation=valuation,
                category=category
            ))


        db.commit()
        print("Populated demo user with random data.")

        # 6. Generate Some History for NAV Chart
        # Simulate last 10 snapshots
        total_qty = db.query(Equity).filter(Equity.user_id == demo_user.id).count() # used as proxy or count
        # In the app total_qty is sum(e.quantity)
        total_equity_qty = sum(e.quantity for e in db.query(Equity).filter(Equity.user_id == demo_user.id).all())
        
        for i in range(20, -1, -1):
            ts = datetime.utcnow() - timedelta(hours=i*2)
            # Add some variability
            multiplier = 1 + (random.uniform(-0.02, 0.05))
            
            # Recalculate based on fixed random data
            # Market value ~ portfolio value or similar
            # Let's just mock it for demo
            mock_val = 15000000 * multiplier
            db.add(NAVHistory(
                user_id=demo_user.id,
                timestamp=ts,
                total_value=mock_val,
                total_invested=12000000,
                nav_per_share=mock_val / total_equity_qty if total_equity_qty > 0 else 0,
                total_shares=total_equity_qty
            ))
        
        db.commit()
        print("Generated demo NAV history.")

    finally:
        db.close()

if __name__ == "__main__":
    populate_demo()
