import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/token', data=b'username=kedar&password=password', headers={'Content-Type': 'application/x-www-form-urlencoded'})
try:
    resp = urllib.request.urlopen(req)
    token = json.loads(resp.read().decode())['access_token']
    
    req2 = urllib.request.Request('http://127.0.0.1:8000/api/auth/radar-config', method='PUT', headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    
    data = {"weight_dip": 12, "weight_rsi": 8, "weight_dma": 12, "weight_breakout": 12, "weight_market_bonus": 6, "weight_pe_discount": 12, "weight_peg": 8, "weight_roe": 10, "weight_roce_nim_ev": 10, "weight_quality_3": 0, "weight_risk_pe": 2, "weight_risk_earnings": 4, "weight_risk_debt": 4, "use_dip": True, "use_rsi": True, "use_dma": True, "use_breakout": True, "use_market_bonus": True, "use_pe_discount": True, "use_peg": True, "use_quality": True, "use_risk": True}
    req2.data = json.dumps(data).encode()
    resp2 = urllib.request.urlopen(req2)
    print(resp2.read().decode())
except Exception as e:
    print(getattr(e, 'read', lambda: b'')().decode() or str(e))
