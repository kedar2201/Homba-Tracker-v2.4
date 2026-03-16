import pandas as pd

path = 'C:/Users/kedar/Downloads/NEW homba stocks 28 aug 2023.xlsx'
df = pd.read_excel(path, sheet_name='all shares details 10 aug', header=None)

for i, row in df.iterrows():
    val = str(row[2]).lower()
    if 'comb' in val or 'total' in val or 'sum' in val:
        print(f"Row {i}: Col2='{row[2]}', Col7={row[7]}, Col9={row[9]}")
    
    # Also check if LTP header repeats
    if 'price' in str(row[4]).lower():
         print(f"Header possibly repeats at Row {i}")
