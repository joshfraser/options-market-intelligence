"""
Polymarket API collector for prediction market data.

Uses Gamma API for market metadata and volume,
and CLOB API for price history.
"""

from collectors import api_get

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"

# Tag IDs for categories (discovered via /tags endpoint)
CRYPTO_TAG_ID = "21"


def fetch_tags():
    """Fetch all available tags/categories."""
    print("  Fetching Polymarket tags...")
    data = api_get(f"{GAMMA_URL}/tags", params={"limit": 200})
    if not data:
        return []
    return data


def fetch_markets(tag_id=None, closed=None, limit=100, offset=0):
    """Fetch markets with optional tag filter."""
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "volume",
        "ascending": "false",
    }
    if tag_id:
        params["tag_id"] = tag_id
    if closed is not None:
        params["closed"] = str(closed).lower()

    data = api_get(f"{GAMMA_URL}/markets", params=params)
    return data if data else []


def fetch_events(tag_id=None, closed=None, limit=100, offset=0):
    """Fetch events with optional tag filter."""
    params = {
        "limit": limit,
        "offset": offset,
    }
    if tag_id:
        params["tag_id"] = tag_id
    if closed is not None:
        params["closed"] = str(closed).lower()

    data = api_get(f"{GAMMA_URL}/events", params=params)
    return data if data else []


def _sum_market_volume(markets):
    """Sum volume across a list of markets."""
    total = 0
    total_24h = 0
    total_1w = 0
    total_1m = 0
    for m in markets:
        total += float(m.get("volumeNum", 0) or 0)
        total_24h += float(m.get("volume24hr", 0) or 0)
        total_1w += float(m.get("volume1wk", 0) or 0)
        total_1m += float(m.get("volume1mo", 0) or 0)
    return {
        "total": total,
        "volume24h": total_24h,
        "volume1w": total_1w,
        "volume1m": total_1m,
    }


def fetch_all_polymarket_data():
    """Fetch comprehensive Polymarket data including crypto vs overall volume."""
    print("\n=== Fetching Polymarket Data ===")

    # Fetch all markets (paginate to get totals)
    print("  Fetching all markets for total volume...")
    all_markets = []
    offset = 0
    batch_size = 100
    while True:
        batch = fetch_markets(limit=batch_size, offset=offset)
        if not batch:
            break
        all_markets.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
        # Safety limit
        if offset > 5000:
            break

    total_volume = _sum_market_volume(all_markets)
    print(f"  Total markets fetched: {len(all_markets)}, Total volume: ${total_volume['total']:,.0f}")

    # Fetch crypto/price prediction markets
    print("  Fetching crypto markets...")
    crypto_markets = []
    offset = 0
    while True:
        batch = fetch_markets(tag_id=CRYPTO_TAG_ID, limit=batch_size, offset=offset)
        if not batch:
            break
        crypto_markets.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
        if offset > 2000:
            break

    crypto_volume = _sum_market_volume(crypto_markets)
    print(f"  Crypto markets: {len(crypto_markets)}, Crypto volume: ${crypto_volume['total']:,.0f}")

    # Calculate percentage
    price_pct = 0
    if total_volume["total"] > 0:
        price_pct = (crypto_volume["total"] / total_volume["total"]) * 100

    # Get top crypto markets for detail
    top_crypto = []
    for m in sorted(crypto_markets, key=lambda x: float(x.get("volumeNum", 0) or 0), reverse=True)[:20]:
        top_crypto.append({
            "question": m.get("question", ""),
            "volume": float(m.get("volumeNum", 0) or 0),
            "volume24h": float(m.get("volume24hr", 0) or 0),
            "liquidity": float(m.get("liquidityNum", 0) or 0),
            "closed": m.get("closed", False),
        })

    # Fetch tags for category breakdown
    tags = fetch_tags()
    tag_map = {}
    if tags:
        for t in tags:
            if isinstance(t, dict):
                tag_map[t.get("id", "")] = t.get("label", "")

    return {
        "totalVolume": total_volume,
        "cryptoVolume": crypto_volume,
        "pricePredictionPct": round(price_pct, 2),
        "totalMarkets": len(all_markets),
        "cryptoMarkets": len(crypto_markets),
        "topCryptoMarkets": top_crypto,
        "totalLiquidity": sum(float(m.get("liquidityNum", 0) or 0) for m in all_markets),
        "cryptoLiquidity": sum(float(m.get("liquidityNum", 0) or 0) for m in crypto_markets),
        "categories": tag_map,
    }
