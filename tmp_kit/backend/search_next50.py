import requests

def search_next50():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    for line in lines:
        if "SBI" in line.upper() and ("NEXT 50" in line.upper() or "NEXT50" in line.upper()):
            print(line)

search_next50()
