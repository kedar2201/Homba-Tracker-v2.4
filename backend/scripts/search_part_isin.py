import requests

def search_part_isin():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    
    print("Results for 'S35':")
    for line in lines:
        if "S35" in line and ";" in line:
            print(line)

search_part_isin()
