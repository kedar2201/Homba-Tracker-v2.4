from datetime import date
from app.services.calculations import calculate_fd_interest_for_fy

try:
    p = 100000
    r = 7.5
    s = date(2023, 10, 1)
    m = date(2025, 10, 1)
    f = "Quarterly"
    fy = 2024
    
    interest = calculate_fd_interest_for_fy(p, r, s, m, f, fy)
    print(f"Interest: {interest}")
except Exception as e:
    print(f"Error: {e}")
