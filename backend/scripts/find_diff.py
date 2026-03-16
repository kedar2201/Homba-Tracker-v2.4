import pandas as pd

def to_float(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        val_str = str(val).strip().replace(",", "").replace("₹", "").replace("-", "0")
        return float(val_str)
    except:
        return 0.0

path = 'C:/Users/kedar/Downloads/NEW homba stocks 28 aug 2023.xlsx'
df = pd.read_excel(path, sheet_name='all shares details 10 aug', header=None)

for i in range(4, len(df)):
    row = df.iloc[i]
    if pd.isna(row[2]) or "TOTAL" in str(row[2]).upper(): continue
    
    scrip = row[2]
    qty = to_float(row[7])
    ltp = to_float(row[6])
    mv_col = to_float(row[9])
    
    calc = qty * ltp
    if abs(calc - mv_col) > 10: # Significance check
        print(f"Row {i} ({scrip}): Calculated={calc}, Col9={mv_col}, Qty={qty}, LTP={ltp}")
