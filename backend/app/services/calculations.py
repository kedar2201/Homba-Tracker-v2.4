from datetime import date
from typing import Dict

def calculate_fd_maturity(principal: float, rate: float, start_date: date, maturity_date: date, frequency: str = "Yearly") -> float:
    # Standard compound interest formula: A = P(1 + r/n)^(nt)
    # frequency mapping
    n_map = {
        "Monthly": 12,
        "Quarterly": 4,
        "Half-Yearly": 2,
        "Yearly": 1,
        "On Maturity": 1 # Assume simple interest for "On Maturity" or just 1 compounding
    }
    n = n_map.get(frequency, 1)
    
    # Calculate years
    days = (maturity_date - start_date).days
    t = days / 365.25
    
    r = rate / 100
    
    maturity_value = principal * (1 + r/n)**(n*t)
    return round(maturity_value, 2)

def calculate_fd_current_value(principal: float, rate: float, start_date: date, frequency: str = "Yearly") -> float:
    if start_date is None:
        return principal
    
    today = date.today()
    if today <= start_date:
        return principal
    
    days_held = (today - start_date).days
    t = days_held / 365.25
    
    n_map = {
        "Monthly": 12,
        "Quarterly": 4,
        "Half-Yearly": 2,
        "Yearly": 1,
        "On Maturity": 1
    }
    n = n_map.get(frequency, 1)
    r = rate / 100
    
    try:
        current_value = principal * (1 + r/n)**(n*t)
        return round(current_value, 2)
    except:
        return principal

def calculate_fd_interest_for_fy(principal: float, rate: float, start_date: date, maturity_date: date, frequency: str, fy_year: int) -> float:
    """
    fy_year is the start of the financial year (e.g., 2023 for 2023-24)
    FY in India: April 1 to March 31
    """
    fy_start = date(fy_year, 4, 1)
    fy_end = date(fy_year + 1, 3, 31)
    
    # Check for overlap
    overlap_start = max(start_date, fy_start)
    overlap_end = min(maturity_date, fy_end)
    
    if overlap_start >= overlap_end:
        return 0.0
        
    # Interest = (Value at end of overlap) - (Value at start of overlap)
    # n mapping
    n_map = {
        "Monthly": 12,
        "Quarterly": 4,
        "Half-Yearly": 2,
        "Yearly": 1,
        "On Maturity": 1
    }
    n = n_map.get(frequency, 1)
    r = rate / 100
    
    # Calculate days from start_date to overlap start and overlap end
    t_start = (overlap_start - start_date).days / 365.25
    t_end = (overlap_end - start_date).days / 365.25
    
    v_start = principal * (1 + r/n)**(n * t_start)
    v_end = principal * (1 + r/n)**(n * t_end)
    
    return round(v_end - v_start, 2)

# Mock Market Prices
MOCK_EQUITY_PRICES = {
    "RELIANCE": 2540.50,
    "TCS": 3410.20,
    "HDFCBANK": 1650.00,
    "INFY": 1420.00
}

MOCK_MF_NAVS = {
    "INF209K01157": 124.50, # Example ISIN
    "INF846K01EW2": 45.20
}

MOCK_GOLD_PRICE = 7750.0 # Per Gram (24K Gold)

def get_equity_current_value(symbol: str, quantity: int, stored_price: float = None) -> float:
    if stored_price and stored_price > 0:
        price = stored_price
    else:
        price = MOCK_EQUITY_PRICES.get(symbol.upper(), 1000.0)
    return round(price * quantity, 2)

def get_mf_current_value(isin: str, units: float) -> float:
    nav = MOCK_MF_NAVS.get(isin, 50.0) # Fallback to 50
    return round(nav * units, 2)

def get_sgb_current_value(units: float) -> float:
    return round(MOCK_GOLD_PRICE * units, 2)
