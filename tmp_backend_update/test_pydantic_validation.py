import requests

def test_api_create():
    # We need a token. Since this is a test on the user's system, 
    # we might not have a direct way to get a token unless we login.
    # But I can try to bypass auth in the router for a second or just check the schema validation.
    
    # Actually, I can just test Pydantic validation locally.
    from app.schemas.equity import EquityCreate, Exchange
    from datetime import date
    
    data = {
        "exchange": "NSE",
        "symbol": "SGBSEP31III GB",
        "scrip_name": "SGBSEP31III GB",
        "instrument_type": "Other",
        "quantity": 255,
        "buy_price": 5873.0,
        "buy_date": "2024-07-12",
        "holder": "MANISHA",
        "isin": "",
        "broker": "Zerodha"
    }
    
    try:
        obj = EquityCreate(**data)
        print("Pydantic Validation PASSED")
        print(obj.dict())
    except Exception as e:
        print(f"Pydantic Validation FAILED: {e}")

if __name__ == "__main__":
    test_api_create()
