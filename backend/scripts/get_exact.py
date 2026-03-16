import requests

def get_exact_line():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    lines = response.text.splitlines()
    for line in lines:
        if line.startswith("119827;"):
            print(line)

get_exact_line()
