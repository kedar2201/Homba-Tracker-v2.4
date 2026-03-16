from app.database import SessionLocal
from app.models.equity import Equity, EquityStatus
from app.models.user import User
import pandas as pd
import os

def generate_user_reports():
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).all()
        
        for user in users:
            print(f"Generating report for User ID: {user.id} ({user.username})")
            
            # Get active equities for this user
            query = db.query(Equity).filter(
                Equity.status == EquityStatus.ACTIVE,
                Equity.user_id == user.id,
                ~Equity.symbol.startswith('SGB')
            )
            df = pd.read_sql(query.statement, db.bind)
            
            if df.empty:
                print(f"No records found for User {user.id}")
                continue
                
            # Select and Rename Columns
            export_df = df[['id', 'symbol', 'quantity', 'buy_price', 'buy_date', 'holder', 'exchange', 'scrip_name']]
            export_df.columns = ['ID', 'Symbol', 'Qty', 'Buy Price', 'Buy Date', 'Holder', 'Exchange', 'Scrip Name']
            export_df = export_df.sort_values(by=['Symbol', 'Buy Date'])
            
            total_qty = export_df['Qty'].sum()
            print(f"  Total Rows: {len(export_df)}")
            print(f"  Total Quantity: {total_qty}")
            
            filename = f"report_user_{user.id}_{user.username}.csv"
            export_df.to_csv(filename, index=False)
            print(f"  Saved to {filename}")
            print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_user_reports()
