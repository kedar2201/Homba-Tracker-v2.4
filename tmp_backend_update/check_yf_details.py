import yfinance as yf
import json
import pandas as pd

def check_stock(symbol):
    print(f"--- Checking {symbol} ---")
    ticker = yf.Ticker(symbol)
    
    # 1. Info
    info = ticker.info
    print("\n[INFO] Basic data:")
    print(f"Price: {info.get('currentPrice')}")
    print(f"Trailing EPS: {info.get('trailingEps')}")
    print(f"Forward EPS: {info.get('forwardEps')}")
    print(f"Trailing PE: {info.get('trailingPE')}")
    print(f"Forward PE: {info.get('forwardPE')}")
    print(f"Earnings Growth: {info.get('earningsGrowth')}")
    
    # 2. Earnings Estimate (if available)
    try:
        earnings_estimate = ticker.earnings_estimates
        if earnings_estimate is not None and not earnings_estimate.empty:
            print("\n[Earnings Estimates]:")
            print(earnings_estimate)
    except Exception as e:
        print(f"\n[Earnings Estimates] Error: {e}")

    # 3. Growth Estimates
    try:
        growth_estimates = ticker.growth_estimates
        if growth_estimates is not None and not growth_estimates.empty:
            print("\n[Growth Estimates]:")
            print(growth_estimates)
    except Exception as e:
        print(f"\n[Growth Estimates] Error: {e}")

    # 4. Income Statement / Balance Sheet (Last 3 Years)
    print("\n[Financials] checking counts...")
    print(f"Income Stmt years: {len(ticker.income_stmt.columns) if ticker.income_stmt is not None else 0}")
    print(f"Balance Sheet years: {len(ticker.balance_sheet.columns) if ticker.balance_sheet is not None else 0}")

if __name__ == "__main__":
    check_stock("RELIANCE.NS")
    # Also check HDFCBANK (Bank)
    check_stock("HDFCBANK.NS")
