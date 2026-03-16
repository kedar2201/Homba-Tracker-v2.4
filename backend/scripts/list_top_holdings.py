from app.database import SessionLocal
from app.models.equity import Equity, EquityStatus
import pandas as pd

def list_top_holdings():
    db = SessionLocal()
    try:
        # Get all active equities
        query = db.query(Equity).filter(
            Equity.status == EquityStatus.ACTIVE,
            ~Equity.symbol.startswith('SGB')
        )
        df = pd.read_sql(query.statement, db.bind)
        
        # Sort by quantity descending
        df_sorted = df.sort_values(by='quantity', ascending=False)
        
        print(f"Top 20 Holdings by Quantity (Total: {df['quantity'].sum()}):")
        print("-" * 60)
        print(f"{'Symbol':<15} {'Holder':<10} {'Qty':<10} {'Price':<10} {'Date':<12}")
        print("-" * 60)
        
        for i, row in df_sorted.head(20).iterrows():
            print(f"{row['symbol']:<15} {row['holder'] or '-':<10} {row['quantity']:<10} {row['buy_price']:<10} {str(row['buy_date']):<12}")
            
        print("-" * 60)
        
        # Also group by symbol to see if one symbol has many small entries
        df_grouped = df.groupby('symbol')['quantity'].sum().sort_values(ascending=False)
        print("\nTop 10 Symbols by Total Quantity:")
        print(df_grouped.head(10))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_top_holdings()
