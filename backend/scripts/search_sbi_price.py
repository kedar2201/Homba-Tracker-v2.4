import requests

def search_sbi_price():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("Results for 'SBI' with NAV around 235:")
    for line in lines:
        if "SBI" in line and ";" in line:
            parts = line.split(';')
            if len(parts) >= 5:
                try:
                    nav = float(parts[4])
                    if 230 <= nav <= 240:
                        print(line)
                except:
                    pass

search_sbi_price()
