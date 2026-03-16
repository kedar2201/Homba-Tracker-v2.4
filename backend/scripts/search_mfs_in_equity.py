import pandas as pd

path = 'C:/Users/kedar/Downloads/NEW homba stocks 28 aug 2023.xlsx'
df = pd.read_excel(path, sheet_name='all shares details 10 aug', header=None)

for i, row in df.iterrows():
    val = str(row[2]).lower()
    if 'mut' in val or 'fund' in val or 'mutf' in val:
        print(f"Row {i}: {row[2]}")
