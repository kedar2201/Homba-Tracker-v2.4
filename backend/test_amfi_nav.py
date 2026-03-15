import requests
import time

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

def test_amfi_fetch():
    print("Fetching AMFI NAV data...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(AMFI_NAV_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print(f"Total lines fetched: {len(lines)}")
        
        # Test ISINs from user's screenshot
        test_isins = {
            "INF179K01WA6": "HDFC Balanced Advantage Fund",
            "INF959L01DD1": "Helios Flexi Cap Fund",
            "INF109K01Z48": "ICICI Prudential Balanced Advantage Fund",
            "INF109K01Z30": "ICICI Prudential Banking and PSU Debt Fund",
            "INF247L01AF9": "Motilal Oswal Nifty 200 Momentum 30 Index Fund",
            "INF082J01BT9": "Quantum Small Cap Fund",
            "INF200K01QX4": "SBI Banking & PSU Fund",
            "INF200K01RA9": "SBI Nifty Index Fund"
        }
        
        found_navs = {}
        
        for line in lines:
            sep = ";" if ";" in line else "|" if "|" in line else None
            if not sep or "Scheme Code" in line:
                continue
            
            parts = line.split(sep)
            if len(parts) < 6:
                continue
                
            scheme_code = parts[0].strip()
            isin1 = parts[1].strip()
            isin2 = parts[2].strip()
            scheme_name = parts[3].strip()
            nav_value = parts[4].strip()
            
            # Check if this line matches any of our test ISINs
            for test_isin, expected_name in test_isins.items():
                if isin1 == test_isin or isin2 == test_isin:
                    try:
                        nav = float(nav_value)
                        found_navs[test_isin] = {
                            'name': scheme_name,
                            'nav': nav,
                            'code': scheme_code
                        }
                        print(f"\n✓ Found: {expected_name}")
                        print(f"  ISIN: {test_isin}")
                        print(f"  AMFI Name: {scheme_name}")
                        print(f"  NAV: ₹{nav}")
                        print(f"  Code: {scheme_code}")
                    except:
                        pass
        
        print(f"\n\nSummary: Found {len(found_navs)} out of {len(test_isins)} funds")
        
        missing = set(test_isins.keys()) - set(found_navs.keys())
        if missing:
            print("\nMissing ISINs:")
            for isin in missing:
                print(f"  - {isin}: {test_isins[isin]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_amfi_fetch()
