from jugaad_data.nse import NSELive
import json

n = NSELive()
try:
    q = n.stock_quote('ACUTAAS')
    print(json.dumps(q['priceInfo']))
except Exception as e:
    print(f"Error: {e}")
