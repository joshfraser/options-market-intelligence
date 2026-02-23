"""
DefiLlama API collector for perps, options, and fee/revenue data.

Free endpoints used:
- /overview/options - options volume overview (historical + per-protocol)
- /summary/options/{protocol} - per-protocol options history
- /overview/fees - fees/revenue overview
- /summary/fees/{protocol} - per-protocol fees/revenue history
- /summary/dexs/{protocol} - per-protocol DEX volume history
- /protocol/{protocol} - TVL history
"""

from collectors import api_get, ts_to_date

BASE_URL = "https://api.llama.fi"

# Known perps protocols and their DefiLlama slugs
PERPS_PROTOCOLS = {
    "hyperliquid": "Hyperliquid",
    "lighter-v2": "Lighter",
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
    "rabbitx": "RabbitX",
}

# Known options protocols
OPTIONS_PROTOCOLS = {
    "deribit": "Deribit",
    "lyra": "Lyra",
    "hegic": "Hegic",
    "premia": "Premia",
    "aevo": "Aevo",
    "thetanuts-finance": "Thetanuts",
    "opyn": "Opyn",
    "derive": "Derive",
    "moby": "Moby",
    "ithaca-protocol": "Ithaca",
    "stryke": "Stryke",
    "typus-finance": "Typus",
    "zeta-markets": "Zeta Markets",
}


def _extract_chart_data(data, key="totalDataChart"):
    """Extract date->value pairs from DefiLlama chart arrays."""
    chart = data.get(key, [])
    if not chart:
        return {}
    result = {}
    for entry in chart:
        if isinstance(entry, list) and len(entry) >= 2:
            date = ts_to_date(entry[0])
            result[date] = entry[1]
    return result


def _extract_breakdown_chart(data, key="totalDataChartBreakdown"):
    """Extract date->{ protocol: value } from DefiLlama breakdown arrays."""
    chart = data.get(key, [])
    if not chart:
        return {}
    result = {}
    for entry in chart:
        if isinstance(entry, list) and len(entry) >= 2:
            date = ts_to_date(entry[0])
            result[date] = entry[1] if isinstance(entry[1], dict) else {}
    return result


def fetch_options_overview():
    """Fetch options volume overview with historical data and per-protocol breakdown."""
    print("Fetching DefiLlama options overview...")
    data = api_get(f"{BASE_URL}/overview/options")
    if not data:
        return None

    result = {
        "totalHistory": _extract_chart_data(data),
        "protocols": {},
    }

    for proto in data.get("protocols", []):
        name = proto.get("name", "")
        slug = proto.get("module", proto.get("defillamaId", "")).lower()
        result["protocols"][name] = {
            "slug": slug,
            "total24h": proto.get("total24h", 0),
            "total7d": proto.get("total7d", 0),
            "total30d": proto.get("total30d", 0),
            "totalAllTime": proto.get("totalAllTime", 0),
            "change_1d": proto.get("change_1d"),
            "change_7d": proto.get("change_7d"),
            "change_1m": proto.get("change_1m"),
            "dailyNotionalVolume": proto.get("dailyNotionalVolume", proto.get("total24h", 0)),
            "dailyPremiumVolume": proto.get("dailyPremiumVolume", 0),
        }

    return result


def fetch_options_protocol(slug):
    """Fetch historical options data for a specific protocol."""
    print(f"  Fetching options data for {slug}...")
    data = api_get(f"{BASE_URL}/summary/options/{slug}")
    if not data:
        return None
    return {
        "name": data.get("name", slug),
        "totalHistory": _extract_chart_data(data),
        "total24h": data.get("total24h", 0),
        "totalAllTime": data.get("totalAllTime", 0),
    }


def fetch_perps_protocol_volume(slug):
    """Fetch historical volume data for a specific perps protocol via dexs endpoint."""
    print(f"  Fetching volume for {slug}...")
    data = api_get(f"{BASE_URL}/summary/dexs/{slug}")
    if not data:
        return None
    return {
        "name": data.get("name", slug),
        "totalHistory": _extract_chart_data(data),
        "total24h": data.get("total24h", 0),
        "total7d": data.get("total7d", 0),
        "total30d": data.get("total30d", 0),
        "totalAllTime": data.get("totalAllTime", 0),
        "change_1d": data.get("change_1d"),
        "change_7d": data.get("change_7d"),
        "change_1m": data.get("change_1m"),
    }


def fetch_protocol_fees(slug):
    """Fetch historical fees and revenue for a protocol."""
    print(f"  Fetching fees/revenue for {slug}...")
    data = api_get(f"{BASE_URL}/summary/fees/{slug}")
    if not data:
        return None

    fees_chart = _extract_chart_data(data, "totalDataChart")

    # Try to extract fees vs revenue from breakdown
    breakdown = data.get("totalDataChartBreakdown", [])
    daily_fees = {}
    daily_revenue = {}
    for entry in breakdown:
        if isinstance(entry, list) and len(entry) >= 2:
            date = ts_to_date(entry[0])
            vals = entry[1] if isinstance(entry[1], dict) else {}
            # DefiLlama breakdown has chain-level data, sum them
            fee_sum = 0
            rev_sum = 0
            for chain_data in vals.values():
                if isinstance(chain_data, dict):
                    fee_sum += chain_data.get("dailyFees", 0) or 0
                    rev_sum += chain_data.get("dailyRevenue", 0) or 0
                elif isinstance(chain_data, (int, float)):
                    fee_sum += chain_data
            daily_fees[date] = fee_sum if fee_sum else fees_chart.get(date, 0)
            daily_revenue[date] = rev_sum

    # If breakdown didn't yield revenue, use top-level data
    if not any(daily_revenue.values()):
        daily_revenue = {}

    return {
        "name": data.get("name", slug),
        "dailyFees": daily_fees if daily_fees else fees_chart,
        "dailyRevenue": daily_revenue if any(daily_revenue.values()) else fees_chart,
        "total24h": data.get("total24h", 0),
        "totalAllTime": data.get("totalAllTime", 0),
        "dailyFees24h": data.get("dailyFees", data.get("total24h", 0)),
        "dailyRevenue24h": data.get("dailyRevenue", 0),
    }


def fetch_fees_overview():
    """Fetch overview of all protocol fees/revenue."""
    print("Fetching DefiLlama fees overview...")
    data = api_get(f"{BASE_URL}/overview/fees")
    if not data:
        return None

    result = {
        "totalHistory": _extract_chart_data(data),
        "protocols": {},
    }

    for proto in data.get("protocols", []):
        name = proto.get("name", "")
        result["protocols"][name] = {
            "dailyFees": proto.get("dailyFees", proto.get("total24h", 0)),
            "dailyRevenue": proto.get("dailyRevenue", 0),
            "total24h": proto.get("total24h", 0),
            "totalAllTime": proto.get("totalAllTime", 0),
        }

    return result


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


def fetch_all_perps_data():
    """Fetch volume, fees, revenue, and TVL for all tracked perps protocols."""
    print("\n=== Fetching Perps Data ===")
    results = {}

    for slug, display_name in PERPS_PROTOCOLS.items():
        print(f"\nProcessing {display_name} ({slug})...")
        proto_data = {
            "displayName": display_name,
            "slug": slug,
        }

        # Volume
        vol = fetch_perps_protocol_volume(slug)
        if vol:
            proto_data["volumeHistory"] = vol["totalHistory"]
            proto_data["volume24h"] = vol.get("total24h", 0)
            proto_data["volume7d"] = vol.get("total7d", 0)
            proto_data["volume30d"] = vol.get("total30d", 0)
            proto_data["volumeAllTime"] = vol.get("totalAllTime", 0)
            proto_data["volumeChange1d"] = vol.get("change_1d")
            proto_data["volumeChange7d"] = vol.get("change_7d")
            proto_data["volumeChange1m"] = vol.get("change_1m")
        else:
            proto_data["volumeHistory"] = {}
            proto_data["volume24h"] = 0

        # Fees/Revenue
        fees = fetch_protocol_fees(slug)
        if fees:
            proto_data["feesHistory"] = fees["dailyFees"]
            proto_data["revenueHistory"] = fees["dailyRevenue"]
            proto_data["fees24h"] = fees.get("dailyFees24h", 0)
            proto_data["revenue24h"] = fees.get("dailyRevenue24h", 0)
        else:
            proto_data["feesHistory"] = {}
            proto_data["revenueHistory"] = {}
            proto_data["fees24h"] = 0
            proto_data["revenue24h"] = 0

        # TVL
        tvl = fetch_protocol_tvl(slug)
        if tvl:
            proto_data["tvlHistory"] = tvl["tvlHistory"]
            proto_data["currentTvl"] = tvl.get("currentTvl", 0)
        else:
            proto_data["tvlHistory"] = {}
            proto_data["currentTvl"] = 0

        results[slug] = proto_data

    return results


def fetch_all_options_data():
    """Fetch volume and fee data for all tracked options protocols."""
    print("\n=== Fetching Options Data ===")

    # Get overview first
    overview = fetch_options_overview()

    results = {}
    # Fetch individual protocol data
    slugs_to_fetch = set(OPTIONS_PROTOCOLS.keys())

    # Also add any protocols found in overview that we haven't listed
    if overview:
        for name, pdata in overview.get("protocols", {}).items():
            slug = pdata.get("slug", "").lower()
            if slug and slug not in slugs_to_fetch:
                # Only add if it has meaningful volume
                if (pdata.get("total24h", 0) or 0) > 10000:
                    slugs_to_fetch.add(slug)
                    OPTIONS_PROTOCOLS[slug] = name

    for slug in slugs_to_fetch:
        display_name = OPTIONS_PROTOCOLS.get(slug, slug)
        print(f"\nProcessing {display_name} ({slug})...")

        proto_data = {
            "displayName": display_name,
            "slug": slug,
        }

        # Volume from options endpoint
        opt = fetch_options_protocol(slug)
        if opt:
            proto_data["volumeHistory"] = opt["totalHistory"]
            proto_data["volume24h"] = opt.get("total24h", 0)
            proto_data["volumeAllTime"] = opt.get("totalAllTime", 0)
        else:
            proto_data["volumeHistory"] = {}
            proto_data["volume24h"] = 0
            proto_data["volumeAllTime"] = 0

        # Add overview data if available
        if overview:
            for name, pdata in overview.get("protocols", {}).items():
                if pdata.get("slug", "").lower() == slug:
                    proto_data["notionalVolume24h"] = pdata.get("dailyNotionalVolume", 0)
                    proto_data["premiumVolume24h"] = pdata.get("dailyPremiumVolume", 0)
                    proto_data["volume24h"] = proto_data.get("volume24h") or pdata.get("total24h", 0)
                    break

        # Fees/Revenue
        fees = fetch_protocol_fees(slug)
        if fees:
            proto_data["feesHistory"] = fees["dailyFees"]
            proto_data["revenueHistory"] = fees["dailyRevenue"]
            proto_data["fees24h"] = fees.get("dailyFees24h", 0)
            proto_data["revenue24h"] = fees.get("dailyRevenue24h", 0)
        else:
            proto_data["feesHistory"] = {}
            proto_data["revenueHistory"] = {}
            proto_data["fees24h"] = 0
            proto_data["revenue24h"] = 0

        results[slug] = proto_data

    return {
        "overview": {
            "totalHistory": overview["totalHistory"] if overview else {},
        },
        "protocols": results,
    }
