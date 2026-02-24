"""
Hyperliquid direct API collector for perpetuals data.

Free, no API key required.
Endpoint: POST https://api.hyperliquid.xyz/info
Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
"""

from collectors import api_post

BASE_URL = "https://api.hyperliquid.xyz/info"

# Known fee rates for estimation (taker fee as conservative estimate)
FEE_RATE = 0.00035  # 0.035% taker fee
REVENUE_SHARE = 0.5  # ~50% of fees estimated as protocol revenue


def fetch_hyperliquid_data():
    """Fetch all perpetuals data from Hyperliquid."""
    print("  Fetching Hyperliquid perps data (direct API)...")

    data = api_post(BASE_URL, {"type": "metaAndAssetCtxs"})
    if not data or not isinstance(data, list) or len(data) < 2:
        print("  Failed to fetch Hyperliquid data")
        return None

    universe = data[0].get("universe", [])
    contexts = data[1]

    if len(universe) != len(contexts):
        print(f"  Warning: universe ({len(universe)}) != contexts ({len(contexts)})")

    total_volume_24h = 0
    total_oi = 0
    markets = []

    for i, (meta, ctx) in enumerate(zip(universe, contexts)):
        name = meta.get("name", f"UNKNOWN-{i}")
        day_ntl_vlm = float(ctx.get("dayNtlVlm", 0))
        open_interest = float(ctx.get("openInterest", 0))
        oracle_px = float(ctx.get("oraclePx", 0))
        funding = float(ctx.get("funding", 0))

        # OI is in coins, convert to USD
        oi_usd = open_interest * oracle_px
        total_volume_24h += day_ntl_vlm
        total_oi += oi_usd

        markets.append({
            "name": name,
            "volume24h": day_ntl_vlm,
            "openInterest": oi_usd,
            "oraclePrice": oracle_px,
            "fundingRate": funding,
        })

    # Estimate fees from volume
    fees_24h = total_volume_24h * FEE_RATE
    revenue_24h = fees_24h * REVENUE_SHARE

    return {
        "displayName": "Hyperliquid",
        "slug": "hyperliquid",
        "volume24h": total_volume_24h,
        "openInterest": total_oi,
        "fees24h": fees_24h,
        "revenue24h": revenue_24h,
        "marketCount": len(markets),
        "topMarkets": sorted(markets, key=lambda m: m["volume24h"], reverse=True)[:10],
    }
