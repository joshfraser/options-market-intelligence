"""
dYdX v4 Indexer API collector for perpetuals data.

Free, no API key required.
Endpoint: GET https://indexer.dydx.trade/v4/perpetualMarkets
Docs: https://docs.dydx.exchange/api_integration-clients/indexer_client
"""

from collectors import api_get

BASE_URL = "https://indexer.dydx.trade/v4"

# dYdX v4 fee rates (taker)
FEE_RATE = 0.0005  # 0.05% taker fee
REVENUE_SHARE = 0.4  # estimated protocol revenue share


def fetch_dydx_data():
    """Fetch all perpetuals market data from dYdX v4 Indexer."""
    print("  Fetching dYdX v4 perps data (direct API)...")

    data = api_get(f"{BASE_URL}/perpetualMarkets")
    if not data:
        print("  Failed to fetch dYdX data")
        return None

    markets_raw = data.get("markets", {})
    if not markets_raw:
        print("  No markets found in dYdX response")
        return None

    total_volume_24h = 0
    total_oi = 0
    total_trades = 0
    markets = []

    for ticker, mkt in markets_raw.items():
        if mkt.get("status") != "ACTIVE":
            continue

        vol_24h = float(mkt.get("volume24H", 0))
        oracle_price = float(mkt.get("oraclePrice", 0))
        # OI is in base asset units, convert to USD
        oi_raw = float(mkt.get("openInterest", 0))
        oi_usd = oi_raw * oracle_price
        trades = int(mkt.get("trades24H", 0))

        total_volume_24h += vol_24h
        total_oi += oi_usd
        total_trades += trades

        markets.append({
            "ticker": ticker,
            "volume24h": vol_24h,
            "openInterest": oi_usd,
            "oraclePrice": oracle_price,
            "trades24h": trades,
            "priceChange24h": mkt.get("priceChange24H"),
            "nextFundingRate": mkt.get("nextFundingRate"),
        })

    fees_24h = total_volume_24h * FEE_RATE
    revenue_24h = fees_24h * REVENUE_SHARE

    return {
        "displayName": "dYdX",
        "slug": "dydx",
        "volume24h": total_volume_24h,
        "openInterest": total_oi,
        "fees24h": fees_24h,
        "revenue24h": revenue_24h,
        "trades24h": total_trades,
        "marketCount": len(markets),
        "topMarkets": sorted(markets, key=lambda m: m["volume24h"], reverse=True)[:10],
    }
