import requests

def search_v30():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    for line in lines:
        if "V30" in line:
            print(line)

search_v30()
