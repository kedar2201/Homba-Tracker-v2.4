from app.database import SessionLocal
from app.models.equity import Equity, EquityStatus
import pandas as pd
import os

def check_similarity():
    db = SessionLocal()
    try:
        # Get all active equities
        query = db.query(Equity).filter(
            Equity.status == EquityStatus.ACTIVE,
            ~Equity.symbol.startswith('SGB')
        )
        df = pd.read_sql(query.statement, db.bind)
        
        print(f"Total Rows: {len(df)}")
        print(f"Total Qty: {df['quantity'].sum()}")
        
        # Group by Symbol and Quantity to see if we have pairs
        # This is the loosest reasonable grouping for "same trade"
        grouped = df.groupby(['symbol', 'quantity'])
        
        potential_dups = []
        
        print("\n--- Analysing common Symbol + Quantity pairs ---")
        for name, group in grouped:
            if len(group) > 1:
                # Check what columns vary within this group
                nunique = group.nunique()
                varying_cols = nunique[nunique > 1].index.tolist()
                
                # Exclude ID from varying check as it's always unique
                if 'id' in varying_cols: varying_cols.remove('id')
                
                if not varying_cols:
                    # This implies exact duplicates (ignoring ID), which we thought we didn't have?
                    # Let's verify
                    potential_dups.append(group)
                else:
                    # They differ by some column
                    print(f"Sym: {name[0]}, Qty: {name[1]} -> Count: {len(group)}. Varying: {varying_cols}")
                    # Print the varying values
                    for col in varying_cols:
                        print(f"  {col}: {group[col].unique()}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_similarity()
