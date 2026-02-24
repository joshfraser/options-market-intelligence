"""
DefiLlama API collector — TVL data only.

The /protocol/{slug} endpoint for TVL is free and reliable.
Volume/fees/revenue data now comes from direct protocol APIs + CoinGecko.
"""

from collectors import api_get, ts_to_date

BASE_URL = "https://api.llama.fi"

# All protocols we track for TVL (perps + options with DeFi TVL)
TVL_PROTOCOLS = {
    # Perps
    "hyperliquid": "Hyperliquid",
    "dydx": "dYdX",
    "gmx-v2": "GMX",
    "vertex-protocol": "Vertex",
    "jupiter-perpetual": "Jupiter Perps",
    "drift-protocol": "Drift",
    "kwenta": "Kwenta",
    "apex-protocol": "ApeX",
    "gains-network": "Gains Network",
    "synthetix": "Synthetix",
    "aevo": "Aevo",
    "bluefin": "Bluefin",
    # Options (DeFi only — Deribit is CeFi, no TVL)
    "lyra": "Lyra",
    "hegic": "Hegic",
    "premia": "Premia",
    "opyn": "Opyn",
    "derive": "Derive",
    "stryke": "Stryke",
}


def fetch_protocol_tvl(slug):
    """Fetch TVL history for a protocol."""
    print(f"  Fetching TVL for {slug}...")
    data = api_get(f"{BASE_URL}/protocol/{slug}")
    if not data:
        return None

    tvl_history = {}
    for entry in data.get("tvl", []):
        if isinstance(entry, dict):
            date = ts_to_date(entry.get("date", 0))
            tvl_history[date] = entry.get("totalLiquidityUSD", 0)

    return {
        "name": data.get("name", slug),
        "tvlHistory": tvl_history,
        "currentTvl": data.get("currentChainTvls", {}).get("total",
                      sum(v for v in data.get("currentChainTvls", {}).values()
                          if isinstance(v, (int, float)))),
    }


def fetch_all_tvl():
    """Fetch TVL for all tracked protocols. Returns { slug: { tvlHistory, currentTvl } }."""
    print("\n=== Fetching TVL Data (DefiLlama) ===")
    results = {}

    for slug, display_name in TVL_PROTOCOLS.items():
        tvl = fetch_protocol_tvl(slug)
        if tvl:
            results[slug] = {
                "displayName": display_name,
                "tvlHistory": tvl["tvlHistory"],
                "currentTvl": tvl.get("currentTvl", 0),
            }
        else:
            results[slug] = {
                "displayName": display_name,
                "tvlHistory": {},
                "currentTvl": 0,
            }

    return results
