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

total_mv = 0
total_iv = 0
rows_processed = 0

for i in range(4, len(df)):
    row = df.iloc[i]
    if pd.isna(row[2]) or "TOTAL" in str(row[2]).upper(): continue
    
    mv = to_float(row[9])  # Market Value
    iv = to_float(row[10]) # Invested Value
    
    total_mv += mv
    total_iv += iv
    rows_processed += 1

print(f"Rows Processed: {rows_processed}")
print(f"Total Market Value (Sheet Col 9): {total_mv}")
print(f"Total Invested Value (Sheet Col 10): {total_iv}")
