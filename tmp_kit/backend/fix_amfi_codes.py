import sqlite3
import requests
import time

DB_PATH = "financial_portfolio.db"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

def fetch_amfi_data():
    """Fetch and parse AMFI NAV data"""
    print("Fetching AMFI data...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(AMFI_URL, headers=headers, timeout=30)
    response.raise_for_status()
    
    # Build lookup dictionaries
    isin_to_code = {}
    name_to_code = {}
    
    for line in response.text.splitlines():
        sep = ";" if ";" in line else None
        if not sep or "Scheme Code" in line:
            continue
            
        parts = line.split(sep)
        if len(parts) < 6:
            continue
            
        scheme_code = parts[0].strip()
        isin1 = parts[1].strip()
        isin2 = parts[2].strip()
        scheme_name = parts[3].strip().upper()
        
        if isin1 and isin1 != '-':
            isin_to_code[isin1] = scheme_code
        if isin2 and isin2 != '-':
            isin_to_code[isin2] = scheme_code
        name_to_code[scheme_name] = scheme_code
    
    print(f"Loaded {len(isin_to_code)} ISIN mappings and {len(name_to_code)} name mappings")
    return isin_to_code, name_to_code

def fix_amfi_codes():
    """Fix AMFI codes for all mutual funds"""
    isin_to_code, name_to_code = fetch_amfi_data()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all mutual funds
    cursor.execute("SELECT id, scheme_name, isin, amfi_code FROM mutual_funds")
    funds = cursor.fetchall()
    
    updated = 0
    for fund_id, scheme_name, isin, current_code in funds:
        correct_code = None
        
        # Try ISIN first
        if isin and isin in isin_to_code:
            correct_code = isin_to_code[isin]
        
        # Try name match if ISIN didn't work
        if not correct_code:
            clean_name = scheme_name.upper().strip()
            if clean_name in name_to_code:
                correct_code = name_to_code[clean_name]
        
        # Update if we found a different code
        if correct_code and correct_code != current_code:
            cursor.execute("UPDATE mutual_funds SET amfi_code = ? WHERE id = ?", (correct_code, fund_id))
            print(f"✓ Updated '{scheme_name}': {current_code} → {correct_code}")
            updated += 1
        elif correct_code:
            print(f"  '{scheme_name}': Already correct ({correct_code})")
        else:
            print(f"✗ '{scheme_name}': No match found")
    
    conn.commit()
    conn.close()
    
    print(f"\nTotal updated: {updated} funds")

if __name__ == "__main__":
    fix_amfi_codes()
