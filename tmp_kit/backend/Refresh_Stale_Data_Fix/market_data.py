import requests
import time
import logging
from .price_providers.service import price_service

logger = logging.getLogger(__name__)

# Simple in-memory cache for MF Fallback
GLOBAL_MARKET_CACHE = {} 
NAME_SEARCH_CACHE = {} # Cache for fuzzy search results
CACHE_EXPIRY_SECONDS = 300 

def get_cached_value(key):
    if key in GLOBAL_MARKET_CACHE:
        val, ts = GLOBAL_MARKET_CACHE[key]
        if time.time() - ts < CACHE_EXPIRY_SECONDS:
            return val
    return None

def set_cached_value(key, value):
    GLOBAL_MARKET_CACHE[key] = (value, time.time())

def fetch_live_stock_prices(symbols, force_refresh: bool = False):
    """
    Fetch live prices and previous close for a list of symbols.
    Uses the configured pluggable price provider with DB caching.
    """
    if not symbols:
        return {}
    
    # Delegate to the pluggable price service
    return price_service.get_prices(symbols, force_refresh=force_refresh)

from dateutil import parser

# AMFI Official Source
AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_NAV_CACHE = {
    "by_code": {},  # schemeCode -> nav
    "by_isin": {},  # isin -> nav
    "by_name": {},  # schemeName -> nav
    "last_fetch": 0
}

def refresh_amfi_nav_cache():
    """
    Fetch the official AMFI text file and parse it into memory.
    """
    now = time.time()
    # Refresh every 6 hours. If currently fetching, skip (simple lock)
    if AMFI_NAV_CACHE["last_fetch"] == -1: # Already fetching
        return
    if AMFI_NAV_CACHE["last_fetch"] > 0 and (now - AMFI_NAV_CACHE["last_fetch"] < 21600):
        return
        
    AMFI_NAV_CACHE["last_fetch"] = -1 # Mark as fetching
    try:
        logger.info("Refreshing AMFI NAV cache from official source...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(AMFI_NAV_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        # Clear existing entries
        temp_code = {}
        temp_isin = {}
        temp_name = {}
        
        for line in lines:
            # Check for separator - AMFI usually uses ; now
            sep = ";" if ";" in line else "|" if "|" in line else None
            if not sep or "Scheme Code" in line:
                continue
            
            parts = line.split(sep)
            if len(parts) < 6:
                continue
                
            scheme_code = parts[0].strip()
            isin1 = parts[1].strip()
            isin2 = parts[2].strip()
            scheme_name = parts[3].strip().upper()
            nav_value = parts[4].strip()
            
            if not nav_value or nav_value.lower() == "n.a.":
                continue
                
            try:
                nav = float(nav_value)
                temp_code[scheme_code] = nav
                if isin1 and isin1 != "-":
                    temp_isin[isin1] = nav
                if isin2 and isin2 != "-":
                    temp_isin[isin2] = nav
                # Store full object to retrieve code later
                temp_name[scheme_name] = {'nav': nav, 'code': scheme_code}
            except ValueError:
                continue
        
        AMFI_NAV_CACHE["by_code"] = temp_code
        AMFI_NAV_CACHE["by_isin"] = temp_isin
        AMFI_NAV_CACHE["by_name"] = temp_name
        AMFI_NAV_CACHE["last_fetch"] = now
        logger.info(f"AMFI Cache refreshed: {len(AMFI_NAV_CACHE['by_code'])} schemes loaded.")
        
    except Exception as e:
        logger.error(f"Failed to refresh AMFI NAV cache: {e}")

def fetch_mf_nav(amfi_code=None, isin=None, skip_remote=False):
    """
    Fetch latest NAV for a mutual fund using its AMFI code or ISIN.
    Official AMFI source is preferred.
    """
    try:
        refresh_amfi_nav_cache()
    except:
        pass # Don't block if AMFI site is down
    
    # 1. Try AMFI Code lookup
    if amfi_code and str(amfi_code) in AMFI_NAV_CACHE["by_code"]:
        return AMFI_NAV_CACHE["by_code"][str(amfi_code)]
        
    # 2. Try ISIN lookup
    if isin and isin in AMFI_NAV_CACHE["by_isin"]:
        return AMFI_NAV_CACHE["by_isin"][isin]
        
    if skip_remote:
        return None

    # 3. Fallback to mfapi.in if AMFI lookup failed
    if amfi_code:
        cached = get_cached_value(f"MF_API_{amfi_code}")
        if cached: return cached
        
        try:
            url = f"https://api.mfapi.in/mf/{amfi_code}"
            response = requests.get(url, timeout=5)
            data = response.json()
            if data and "data" in data and len(data["data"]) > 0:
                nav = float(data["data"][0]["nav"])
                set_cached_value(f"MF_API_{amfi_code}", nav)
                return nav
        except Exception:
            pass
            
    return None

# Result cache for searching by name to avoid O(N*M) loops
# name -> {nav, code}
NAME_SEARCH_CACHE = {}

def search_mf_nav_by_name(scheme_name, allow_refresh=True):
    """
    Search for a fund by name and get its latest NAV using AMFI official list.
    Returns dict: {'nav': float, 'code': str} or None
    """
    if not scheme_name:
        return None
    
    if allow_refresh:
        refresh_amfi_nav_cache()
    
    name_upper = scheme_name.upper().replace("MF-", "").replace("MF ", "").replace("MUTAL", "MUTUAL").strip()
    
    # 0. Check pre-computed search results cache
    if name_upper in NAME_SEARCH_CACHE:
        val_obj, ts = NAME_SEARCH_CACHE[name_upper]
        if time.time() - ts < 86400: # Cache name matches for 24 hours
            return val_obj
    
    # 1. Exact match in AMFI cache
    if name_upper in AMFI_NAV_CACHE["by_name"]:
        return AMFI_NAV_CACHE["by_name"][name_upper]
        
    # 2. Smart Search
    clean_target = name_upper.replace("-", " ").replace("(", " ").replace(")", " ")
    is_direct = "DIRECT" in clean_target or "DIR" in clean_target
    is_regular = "REGULAR" in clean_target or " REG " in clean_target
    
    stop_words = ["MF", "FUND", "PLAN", "MUTUAL", "MUTAL", "SCHEME", "INDIA", "LTD", "LIMITED", "THE", "OF", "ADVISORY"]
    target_words = [w for w in clean_target.split() if w not in stop_words and len(w) >= 2]
    
    if not target_words:
        return None
        
    # Filter candidates
    candidates = []
    target_brand = target_words[0]
    
    # Critical keywords that must match if present in query, or must NOT be in result if NOT in query
    crucial_keywords = ["BANK", "TITAN", "NIFTY", "SENSEX", "GOLD", "SILVER", "TAX", "ELSS", "BLUECHIP", "MIDCAP", "SMALLCAP", "LARGE", "ARBITRAGE"]
    query_crucial = [w for w in crucial_keywords if w in clean_target]
    
    for amfi_name, data in AMFI_NAV_CACHE["by_name"].items():
        if target_brand not in amfi_name:
            continue
            
        score = 0
        amfi_words = [w for w in amfi_name.replace("-", " ").replace("(", " ").replace(")", " ").split() if w not in stop_words and len(w) >= 2]
        
        # Word overlap score
        matches = 0
        for w in target_words:
            if w in amfi_name:
                matches += 1
                score += 15
            elif any(w in aw for aw in amfi_words):
                score += 10
        
        # Penalty for extra crucial words in AMFI name that are NOT in target
        for cw in crucial_keywords:
            if cw in amfi_name and cw not in query_crucial:
                score -= 60 # Strong penalty for funds like "Bank Index" matching "Index"
        
        # Penalty for extra words in AMFI name in general (prefer shorter matches)
        extra_words = len(amfi_words) - len(target_words)
        if extra_words > 0:
            score -= extra_words * 2
        
        # Rule: Direct vs Regular
        amfi_is_direct = "DIRECT" in amfi_name or " DIR " in amfi_name
        if is_direct:
            if amfi_is_direct: score += 40
            else: score -= 80
        elif is_regular:
            if not amfi_is_direct: score += 40
            else: score -= 80
        else:
            # User didn't specify. Prefer DIRECT slightly in modern portfolios, or just don't penalize
            if amfi_is_direct: score += 10
            
        # Rule: Growth vs IDCW
        is_idcw_query = any(k in clean_target for k in ["IDCW", "PAYOUT", "DIVIDEND", "INCOME"])
        amfi_is_idcw = any(k in amfi_name for k in ["IDCW", "PAYOUT", "DIVIDEND", "INCOME"])
        
        if is_idcw_query:
            if amfi_is_idcw: score += 50
            else: score -= 100
        else:
            if not amfi_is_idcw:
                score += 30 # Prefer Growth
                if "GROWTH" in amfi_name: score += 10
            else:
                score -= 70 # Heavy penalty for IDCW if not requested
            
        candidates.append((amfi_name, data['nav'], score, data['code']))
            
    if not candidates:
        return None
        
    candidates.sort(key=lambda c: c[2], reverse=True)
    best_match = candidates[0]
    
    if best_match[2] < 20: # Higher threshold for safety
        logger.warning(f"Low confidence match for '{scheme_name}': {best_match[0]} (Score={best_match[2]})")
        return None
        
    logger.info(f"MF MATCH: '{scheme_name}' -> '{best_match[0]}' NAV={best_match[1]} (Score={best_match[2]})")
    
    result_obj = {'nav': best_match[1], 'code': best_match[3]}
    NAME_SEARCH_CACHE[name_upper] = (result_obj, time.time())
    return result_obj

# Keep track of search results to avoid hitting Yahoo repeatedly
# name -> {ticker: str, timestamp: float}
TICKER_SEARCH_CACHE = {}
# Keep track of failed searches to avoid retrying immediately
# name -> last_fail_timestamp
TICKER_SEARCH_BLOCK = {}

def search_ticker_by_name(query):
    """
    Search for a market ticker given a descriptive name or ISIN.
    Useful as a fallback for equities without clear symbols.
    Prioritizes NSE (.NS) over BSE (.BO).
    """
    if not query or len(str(query)) < 3:
        return None
    
    query_clean = str(query).strip().upper()
    
    # 1. Check cache
    if query_clean in TICKER_SEARCH_CACHE:
        entry = TICKER_SEARCH_CACHE[query_clean]
        if time.time() - entry['ts'] < 86400: # 24 hour cache
            return entry['ticker']
            
    # 2. Check block list (don't retry failed searches for 1 hour)
    if query_clean in TICKER_SEARCH_BLOCK:
        if time.time() - TICKER_SEARCH_BLOCK[query_clean] < 3600:
            return None
        
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query_clean}&quotesCount=5&newsCount=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        quotes = data.get("quotes", [])
        if quotes:
            # Prioritize Indian tickers (.NS first, then .BO)
            target_ticker = None
            
            # Look for NSE first
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS"):
                    target_ticker = symbol
                    break
            
            # If no NSE found, look for BSE
            if not target_ticker:
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".BO"):
                        target_ticker = symbol
                        break
            
            # If still nothing, take the first one if it looks remotely correct
            if not target_ticker:
                target_ticker = quotes[0].get("symbol")
            
            if target_ticker:
                TICKER_SEARCH_CACHE[query_clean] = {'ticker': target_ticker, 'ts': time.time()}
                return target_ticker
                
        # If we got here, no ticker was found
        TICKER_SEARCH_BLOCK[query_clean] = time.time()
        
    except Exception as e:
        logger.error(f"Error searching for ticker {query_clean}: {e}")
        # Mark as failed to avoid spike
        TICKER_SEARCH_BLOCK[query_clean] = time.time()
        
    return None

import pandas as pd # Needed for the iloc check above
