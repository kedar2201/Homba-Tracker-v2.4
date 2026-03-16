import pandas as pd

def inspect_others():
    path = "C:/Users/kedar/Downloads/fd23-24-Aug .xlsx"
    df = pd.read_excel(path, sheet_name="nov2023", header=None)
    
    keywords = ["saving", "sb a/c", "gold", "bond", "lic", "ppf", "epf", "post office", "loan", "plot", "land", "flat", "shop"]
    found_categories = []
    
    for k in keywords:
        mask = df.apply(lambda row: row.astype(str).str.contains(k, case=False).any(), axis=1)
        matches = df[mask]
        if not matches.empty:
            print(f"\n=== Mapped Category: {k.upper()} ===")
            # Show first 5 rows of matches to see structure
            for _, row in matches.head(5).iterrows():
                print(f"Row {row.name}: {list(row)}")

if __name__ == "__main__":
    inspect_others()
