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

total_mv_from_col9 = 0
total_mv_calculated = 0
for i in range(4, len(df)):
    row = df.iloc[i]
    if pd.isna(row[2]): continue
    
    mv_col = to_float(row[9]) # Market Value column
    qty = to_float(row[7])   # Available Qty
    ltp = to_float(row[6])   # LTP
    
    total_mv_from_col9 += mv_col
    total_mv_calculated += (qty * ltp)

print(f"Total Market Value from Col 9: {total_mv_from_col9}")
print(f"Total Market Value Calculated (Qty * LTP): {total_mv_calculated}")
