import requests

def search_nifty_index_clean():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("All SBI NIFTY INDEX entries (Clean):")
    for line in lines:
        if "SBI" in line.upper() and "NIFTY INDEX FUND" in line.upper() and ";" in line:
            # Print specific fields to avoid truncation issues in my thought process
            parts = line.split(';')
            if len(parts) >= 6:
                print(f"Code: {parts[0]} | ISIN1: {parts[1]} | ISIN2: {parts[2]} | Name: {parts[3]} | NAV: {parts[4]}")

search_nifty_index_clean()
