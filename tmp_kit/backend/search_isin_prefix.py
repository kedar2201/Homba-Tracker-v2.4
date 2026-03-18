import requests

def search_isin_prefix():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("Results for 'INF200K01':")
    for line in lines:
        if "INF200K01" in line and ";" in line:
            print(line)

search_isin_prefix()
