import requests

def search_nifty_index_all():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("All SBI Nifty Index entries:")
    for line in lines:
        if "SBI" in line.upper() and "NIFTY INDEX FUND" in line.upper() and ";" in line:
            print(line)

search_nifty_index_all()
