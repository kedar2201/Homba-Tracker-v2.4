import requests
import time

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

def simulate_search(scheme_name):
    print(f"Simulating search for: {scheme_name}")
    response = requests.get(AMFI_NAV_URL)
    lines = response.text.splitlines()
    
    by_name = {}
    for line in lines:
        if ";" in line:
            parts = line.split(";")
            if len(parts) > 4:
                code = parts[0].strip()
                name = parts[3].strip().upper()
                nav = parts[4].strip()
                try:
                    by_name[name] = {'nav': float(nav), 'code': code}
                except:
                    continue

    name_upper = scheme_name.upper().strip()
    clean_target = name_upper.replace("-", " ").replace("(", " ").replace(")", " ")
    is_direct = "DIRECT" in clean_target or "DIR" in clean_target
    target_words = [w for w in clean_target.split() if len(w) > 2]
    target_brand = target_words[0]

    candidates = []
    for amfi_name, data in by_name.items():
        if target_brand not in amfi_name:
            continue
            
        score = 0
        match_count = sum(1 for w in target_words if w in amfi_name)
        score += match_count * 10
        
        amfi_is_direct = "DIRECT" in amfi_name or " DIR " in amfi_name
        if is_direct == amfi_is_direct:
            score += 20
        else:
            score -= 50
            
        candidates.append((amfi_name, data['nav'], score, data['code']))
            
    if not candidates:
        print("No candidates found.")
        return
        
    sorted_candidates = sorted(candidates, key=lambda c: c[2], reverse=True)
    print("\nTop Candidates:")
    for c in sorted_candidates[:10]:
        print(f"Score: {c[2]} | NAV: {c[1]} | Code: {c[3]} | Name: {c[0]}")

if __name__ == "__main__":
    simulate_search("SBI Nifty Index Fund")
