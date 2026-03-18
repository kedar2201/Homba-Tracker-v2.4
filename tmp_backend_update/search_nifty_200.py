import requests

def search_nifty_200():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    for line in lines:
        if "SBI" in line.upper() and "NIFTY" in line.upper() and ";" in line:
            parts = line.split(';')
            if len(parts) >= 5:
                try:
                    nav = float(parts[4])
                    if nav > 200:
                        print(line)
                except:
                    pass

search_nifty_200()
