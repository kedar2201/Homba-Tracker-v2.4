from app.database import SessionLocal
from app.models.equity import Equity, EquityStatus
import pandas as pd
import os

def generate_full_report():
    db = SessionLocal()
    try:
        # Get all active equities
        query = db.query(Equity).filter(
            Equity.status == EquityStatus.ACTIVE,
            ~Equity.symbol.startswith('SGB')
        )
        df = pd.read_sql(query.statement, db.bind)
        
        # Select and Rename Columns for readability
        export_df = df[['id', 'symbol', 'quantity', 'buy_price', 'buy_date', 'holder', 'exchange', 'scrip_name']]
        export_df.columns = ['ID', 'Symbol', 'Qty', 'Buy Price', 'Buy Date', 'Holder', 'Exchange', 'Scrip Name']
        
        # Sort by Symbol then Date
        export_df = export_df.sort_values(by=['Symbol', 'Buy Date'])
        
        # Calculate Stats
        total_qty = export_df['Qty'].sum()
        total_rows = len(export_df)
        
        print(f"Generated report for {total_rows} rows.")
        print(f"Total Quantity: {total_qty}")
        
        # Save to CSV
        file_path = os.path.join(os.getcwd(), "full_equity_report.csv")
        export_df.to_csv(file_path, index=False)
        print(f"Report saved to: {file_path}")
        
        # Preview top high-quantity rows for immediate console view
        print("\nTop 10 Entries by Quantity:")
        print(export_df.sort_values(by='Qty', ascending=False).head(10).to_string(index=False))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_full_report()
