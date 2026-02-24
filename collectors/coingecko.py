"""
CoinGecko free-tier API collector for derivatives exchange data.

Free Demo tier: 10,000 calls/month, 30 calls/min, no API key needed.
Base URL: https://api.coingecko.com/api/v3
Docs: https://docs.coingecko.com/reference/derivatives-exchanges

Used as a fallback for protocols not covered by direct API integrations
(Hyperliquid, dYdX, Deribit have their own collectors).
"""

import time
from collectors import api_get

BASE_URL = "https://api.coingecko.com/api/v3"

# Map CoinGecko exchange IDs to our internal protocol slugs.
# CoinGecko IDs are discovered at runtime; these are known mappings.
EXCHANGE_ID_MAP = {
    "gmx": "gmx-v2",
    "gmx_v2": "gmx-v2",
    "jupiter_perpetual": "jupiter-perpetual",
    "jupiter": "jupiter-perpetual",
    "drift_protocol": "drift-protocol",
    "drift": "drift-protocol",
    "vertex_protocol": "vertex-protocol",
    "vertex": "vertex-protocol",
    "kwenta": "kwenta",
    "gains_network": "gains-network",
    "gains-network": "gains-network",
    "synthetix": "synthetix",
    "aevo": "aevo",
    "bluefin": "bluefin",
    "apex_protocol": "apex-protocol",
    "apex-protocol": "apex-protocol",
    "rabbitx": "rabbitx",
    "lighter": "lighter-v2",
    "hyperliquid": "hyperliquid",
    "dydx_perpetual": "dydx",
    "dydx": "dydx",
}

# Display names for our protocols
DISPLAY_NAMES = {
    "gmx-v2": "GMX",
    "jupiter-perpetual": "Jupiter Perps",
    "drift-protocol": "Drift",
    "vertex-protocol": "Vertex",
    "kwenta": "Kwenta",
    "gains-network": "Gains Network",
    "synthetix": "Synthetix",
    "aevo": "Aevo",
    "bluefin": "Bluefin",
    "apex-protocol": "ApeX",
    "rabbitx": "RabbitX",
    "lighter-v2": "Lighter",
    "hyperliquid": "Hyperliquid",
    "dydx": "dYdX",
}

# Estimated fee rates (taker fee as % of volume)
FEE_RATES = {
    "gmx-v2": 0.0007,       # 0.07%
    "jupiter-perpetual": 0.0006,  # 0.06%
    "drift-protocol": 0.0005,
    "vertex-protocol": 0.0002,
    "kwenta": 0.0006,
    "gains-network": 0.0008,
    "synthetix": 0.0006,
    "aevo": 0.0005,
    "bluefin": 0.0004,
    "apex-protocol": 0.0005,
    "rabbitx": 0.0004,
    "lighter-v2": 0.0004,
}
DEFAULT_FEE_RATE = 0.0005
REVENUE_SHARE = 0.3  # Conservative estimate for DeFi protocols


def fetch_derivatives_exchanges():
    """
    Fetch all derivatives exchanges from CoinGecko free tier.
    Returns a dict of { our_slug: { volume24h, openInterest, ... } }.
    """
    print("  Fetching CoinGecko derivatives exchanges (free tier)...")

    # CoinGecko paginates at 100 per page
    all_exchanges = []
    for page in range(1, 4):  # up to 300 exchanges
        data = api_get(
            f"{BASE_URL}/derivatives/exchanges",
            params={"per_page": 100, "page": page},
        )
        if not data or not isinstance(data, list):
            break
        all_exchanges.extend(data)
        if len(data) < 100:
            break
        time.sleep(1)  # Extra delay for CoinGecko free tier

    if not all_exchanges:
        print("  No derivatives exchanges returned from CoinGecko")
        return {}

    print(f"  Found {len(all_exchanges)} derivatives exchanges on CoinGecko")

    # Get current BTC price for converting OI (reported in BTC)
    btc_price = _get_btc_price()

    results = {}
    for exch in all_exchanges:
        cg_id = exch.get("id", "").lower()

        # Try to map to our protocol slug
        our_slug = EXCHANGE_ID_MAP.get(cg_id)
        if not our_slug:
            # Try fuzzy match on name
            name_lower = exch.get("name", "").lower()
            for key, slug in EXCHANGE_ID_MAP.items():
                if key in name_lower:
                    our_slug = slug
                    break

        if not our_slug:
            continue

        oi_btc = float(exch.get("open_interest_btc", 0) or 0)
        vol_btc = float(str(exch.get("trade_volume_24h_btc", 0) or 0).replace(",", ""))

        vol_usd = vol_btc * btc_price
        oi_usd = oi_btc * btc_price

        fee_rate = FEE_RATES.get(our_slug, DEFAULT_FEE_RATE)
        fees_24h = vol_usd * fee_rate
        revenue_24h = fees_24h * REVENUE_SHARE

        results[our_slug] = {
            "displayName": DISPLAY_NAMES.get(our_slug, exch.get("name", our_slug)),
            "slug": our_slug,
            "volume24h": vol_usd,
            "openInterest": oi_usd,
            "fees24h": fees_24h,
            "revenue24h": revenue_24h,
            "perpetualPairs": exch.get("number_of_perpetual_pairs", 0),
            "futuresPairs": exch.get("number_of_futures_pairs", 0),
            "source": "coingecko",
        }

    return results


def _get_btc_price():
    """Get current BTC price in USD from CoinGecko."""
    data = api_get(
        f"{BASE_URL}/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )
    if data and "bitcoin" in data:
        return data["bitcoin"].get("usd", 60000)
    return 60000  # Fallback estimate
