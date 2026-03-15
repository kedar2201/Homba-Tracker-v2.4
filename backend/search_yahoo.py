import requests

def search_yahoo(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        print(f"Results for '{query}':")
        for q in data.get('quotes', []):
            print(f"  {q['symbol']} - {q.get('longname', q.get('shortname'))}")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    search_yahoo("SGBSEP31")
