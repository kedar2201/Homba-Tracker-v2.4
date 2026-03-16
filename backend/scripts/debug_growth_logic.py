
import sys
import os
from datetime import datetime, timedelta

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.nav_history import NAVHistory
from app.models.user import User
from app.services.price_providers.service import price_service

def test_growth_logic():
    db = SessionLocal()
    user_id = 1 # Demo user

    # 1. Fetch History
    # Get last 365 days
    cutoff_date = (datetime.utcnow().date() - timedelta(days=365))
    
    history_records = db.query(NAVHistory).filter(
        NAVHistory.user_id == user_id,
        NAVHistory.timestamp >= cutoff_date
    ).order_by(NAVHistory.timestamp.asc()).all()
    
    if not history_records:
        print("No history records found!")
        return

    portfolio_history = {}
    dates = []
    for record in history_records:
        dt_str = record.timestamp.strftime("%Y-%m-%d")
        portfolio_history[dt_str] = record.total_value
        dates.append(dt_str)
        
    start_date_str = dates[0]
    print(f"Start Date: {start_date_str}")
    
    # 2. Fetch Benchmark
    symbols_to_fetch = ["^NSEI", "^BSESN"]
    print(f"Fetching benchmark from {start_date_str}...")
    benchmark_data = price_service.get_history_bulk(symbols_to_fetch, start_date_str)
    
    nifty_data = benchmark_data.get("^NSEI", {})
    
    # 3. Simulate Loop
    combined_data = []
    
    for dt_str in dates:
        port_val = portfolio_history.get(dt_str, 0)
        nifty_val = nifty_data.get(dt_str, 0)
        
        # Forward fill logic simulation
        if nifty_val == 0:
             keys = sorted([k for k in nifty_data.keys() if k < dt_str], reverse=True)
             if keys: 
                 nifty_val = nifty_data[keys[0]]
             else:
                 pass # Remains 0 if no previous key
                 
        combined_data.append({
            "date": dt_str,
            "portfolio_val": port_val,
            "nifty": nifty_val
        })
        
    # 4. Check Base Values
    if not combined_data:
        print("Combined data empty")
        return
        
    base = combined_data[0]
    print(f"Base Row (Date {base['date']}): Portfolio={base['portfolio_val']}, Nifty={base['nifty']}")
    
    if base['nifty'] == 0:
        print("CRITICAL: Base Nifty is 0! All Nifty growth % will be 0.")
    else:
        print(f"Base Nifty is valid: {base['nifty']}")
        
    # Print first few non-zero nifty rows to see when it starts
    for i, row in enumerate(combined_data[:10]):
        print(f"Row {i} ({row['date']}): Port={row['portfolio_val']}, Nifty={row['nifty']}")

if __name__ == "__main__":
    test_growth_logic()
