import requests

def search_sbi_nifty():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("Results for 'SBI Nifty Index':")
    for line in lines:
        if "SBI Nifty Index" in line and ";" in line:
            print(line)

search_sbi_nifty()
