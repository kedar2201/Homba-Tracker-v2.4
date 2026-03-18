from app.services.market_data import search_ticker_by_name

def find_correct_sgb_ticker():
    queries = ["SGBSEP31II", "SGB SEP 2031 Series II", "IN0020230093"]
    for q in queries:
        print(f"Searching for query: {q}")
        ticker = search_ticker_by_name(q)
        print(f"Found ticker: {ticker}")

if __name__ == "__main__":
    find_correct_sgb_ticker()
