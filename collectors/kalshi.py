"""
Kalshi API collector for prediction market data.

Uses the public trade API v2 for market data, volume, and trade history.
"""

from collectors import api_get

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


def fetch_markets(status="open", limit=200, cursor=None, event_ticker=None, series_ticker=None):
    """Fetch markets from Kalshi."""
    params = {
        "limit": min(limit, 1000),
        "status": status,
    }
    if cursor:
        params["cursor"] = cursor
    if event_ticker:
        params["event_ticker"] = event_ticker
    if series_ticker:
        params["series_ticker"] = series_ticker

    data = api_get(f"{BASE_URL}/markets", params=params)
    if not data:
        return [], None
    markets = data.get("markets", [])
    next_cursor = data.get("cursor", None)
    return markets, next_cursor


def fetch_events(status=None, series_ticker=None, limit=200, cursor=None):
    """Fetch events from Kalshi."""
    params = {"limit": min(limit, 200)}
    if status:
        params["status"] = status
    if series_ticker:
        params["series_ticker"] = series_ticker
    if cursor:
        params["cursor"] = cursor

    data = api_get(f"{BASE_URL}/events", params=params)
    if not data:
        return [], None
    events = data.get("events", [])
    next_cursor = data.get("cursor", None)
    return events, next_cursor


def _sum_market_volume(markets):
    """Sum volume and OI across markets."""
    total_volume = 0
    total_volume_24h = 0
    total_oi = 0
    for m in markets:
        total_volume += int(m.get("volume", 0) or 0)
        total_volume_24h += int(m.get("volume_24h", 0) or 0)
        total_oi += int(m.get("open_interest", 0) or 0)
    return {
        "totalContracts": total_volume,
        "contracts24h": total_volume_24h,
        "openInterest": total_oi,
    }


def _is_crypto_market(market):
    """Determine if a market is crypto-related based on title/category."""
    title = (market.get("title", "") + " " + market.get("subtitle", "")).lower()
    crypto_keywords = [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "sol",
        "xrp", "ripple", "dogecoin", "doge", "cardano", "ada",
        "polygon", "matic", "avalanche", "avax", "chainlink", "link",
        "polkadot", "dot", "uniswap", "uni", "litecoin", "ltc",
        "binance", "bnb", "tether", "usdt", "usdc", "stablecoin",
        "defi", "nft", "blockchain", "token", "altcoin", "memecoin",
    ]
    return any(kw in title for kw in crypto_keywords)


def _is_price_prediction(market):
    """Determine if a market is specifically a price prediction (binary option on price)."""
    title = (market.get("title", "") + " " + market.get("subtitle", "")).lower()
    price_keywords = [
        "price", "above", "below", "reach", "hit", "trade at",
        "end above", "end below", "close above", "close below",
        "higher than", "lower than", "between",
    ]
    return _is_crypto_market(market) and any(kw in title for kw in price_keywords)


def fetch_all_kalshi_data():
    """Fetch comprehensive Kalshi market data."""
    print("\n=== Fetching Kalshi Data ===")

    # Fetch all open markets (paginate)
    print("  Fetching all open markets...")
    all_markets = []
    cursor = None
    while True:
        markets, cursor = fetch_markets(status="open", limit=1000, cursor=cursor)
        if not markets:
            break
        all_markets.extend(markets)
        if not cursor:
            break
        # Safety limit
        if len(all_markets) > 10000:
            break

    # Also get recently closed for volume data
    print("  Fetching recently closed markets...")
    closed_markets = []
    cursor = None
    page_count = 0
    while page_count < 5:  # limit pages for closed markets
        markets, cursor = fetch_markets(status="closed", limit=1000, cursor=cursor)
        if not markets:
            break
        closed_markets.extend(markets)
        page_count += 1
        if not cursor:
            break

    all_combined = all_markets + closed_markets
    print(f"  Total markets: {len(all_combined)} ({len(all_markets)} open, {len(closed_markets)} closed)")

    # Calculate totals
    total_stats = _sum_market_volume(all_combined)
    open_stats = _sum_market_volume(all_markets)

    # Filter crypto markets
    crypto_markets = [m for m in all_combined if _is_crypto_market(m)]
    price_prediction_markets = [m for m in all_combined if _is_price_prediction(m)]

    crypto_stats = _sum_market_volume(crypto_markets)
    price_stats = _sum_market_volume(price_prediction_markets)

    print(f"  Crypto markets: {len(crypto_markets)}, Volume: {crypto_stats['totalContracts']} contracts")
    print(f"  Price predictions: {len(price_prediction_markets)}, Volume: {price_stats['totalContracts']} contracts")

    # Percentage calculations
    crypto_pct = 0
    price_pct = 0
    if total_stats["totalContracts"] > 0:
        crypto_pct = (crypto_stats["totalContracts"] / total_stats["totalContracts"]) * 100
        price_pct = (price_stats["totalContracts"] / total_stats["totalContracts"]) * 100

    # Top crypto markets
    top_crypto = []
    for m in sorted(crypto_markets, key=lambda x: int(x.get("volume", 0) or 0), reverse=True)[:20]:
        top_crypto.append({
            "title": m.get("title", ""),
            "subtitle": m.get("subtitle", ""),
            "volume": int(m.get("volume", 0) or 0),
            "volume24h": int(m.get("volume_24h", 0) or 0),
            "openInterest": int(m.get("open_interest", 0) or 0),
            "isPricePrediction": _is_price_prediction(m),
        })

    return {
        "totalStats": total_stats,
        "openStats": open_stats,
        "cryptoStats": crypto_stats,
        "priceStats": price_stats,
        "cryptoPct": round(crypto_pct, 2),
        "pricePredictionPct": round(price_pct, 2),
        "totalMarkets": len(all_combined),
        "openMarkets": len(all_markets),
        "cryptoMarkets": len(crypto_markets),
        "pricePredictionMarkets": len(price_prediction_markets),
        "topCryptoMarkets": top_crypto,
    }
