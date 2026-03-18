from app.routers.market import get_market_indices
import time

print("Testing market indices fetch...")
start = time.time()
res = get_market_indices()
end = time.time()
print(f"Indices: {res}")
print(f"Time taken: {end-start:.2f} seconds")
