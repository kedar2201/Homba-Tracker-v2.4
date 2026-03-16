import requests

def search_ticker_by_name(name):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={name}&quotesCount=5&newsCount=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        quotes = data.get("quotes", [])
        if quotes:
            # Prefer Indian tickers (.NS or .BO)
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS") or symbol.endswith(".BO"):
                    return symbol
            # Otherwise return first one
            return quotes[0].get("symbol")
    except Exception as e:
        print(f"Error searching for {name}: {e}")
    return None

if __name__ == "__main__":
    test_names = ["RELIANCE INDUSTRIES LTD", "TATA MOTORS", "ASIAN PAINTS"]
    for name in test_names:
        print(f"{name} -> {search_ticker_by_name(name)}")
