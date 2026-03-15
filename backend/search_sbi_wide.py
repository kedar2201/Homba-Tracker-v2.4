import requests

def search_sbi_wide():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("Results for 'SBI' and 'Nifty Index':")
    for line in lines:
        if "SBI" in line and "Nifty Index" in line and ";" in line:
            print(line)

search_sbi_wide()
