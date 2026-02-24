#!/usr/bin/env python3
"""
Daily data updater for the crypto derivatives market intelligence dashboard.

Usage:
    python update_data.py

Data sources:
- Hyperliquid direct API (perps — free, no key)
- dYdX v4 Indexer API (perps — free, no key)
- Deribit public API (options — free, no key)
- CoinGecko free tier (other perps protocols — free, no key)
- DefiLlama (TVL only — free, no key)
- Polymarket / Kalshi (prediction markets — free)

Historical timeseries are accumulated daily in data/history.json.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

from collectors.hyperliquid import fetch_hyperliquid_data
from collectors.dydx import fetch_dydx_data
from collectors.deribit_api import fetch_deribit_options_data
from collectors.coingecko import fetch_derivatives_exchanges
from collectors.defillama import fetch_all_tvl
from collectors.polymarket import fetch_all_polymarket_data
from collectors.kalshi import fetch_all_kalshi_data

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# Protocols tracked for perps (slug -> display name)
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

# Protocols tracked for options
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


def load_history():
    """Load existing historical snapshots."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"snapshots": [], "predictionHistory": [], "perpsDaily": {}, "optionsDaily": {}}


def save_history(history):
    """Save historical snapshots."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def load_previous_data(filename):
    """Load previously saved raw data to preserve historical timeseries."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


# ── Data fetching ──────────────────────────────────────────────────────


def fetch_all_perps_data():
    """
    Fetch perps data from multiple free sources:
    1. Hyperliquid direct API (most volume)
    2. dYdX v4 Indexer (second largest)
    3. CoinGecko free tier (remaining protocols)
    4. DefiLlama (TVL only)

    Merges with previously saved historical timeseries.
    """
    print("\n=== Fetching Perps Data ===")
    results = {}

    # Initialize all protocols with defaults
    for slug, name in PERPS_PROTOCOLS.items():
        results[slug] = {
            "displayName": name,
            "slug": slug,
            "volume24h": 0,
            "volume7d": 0,
            "volume30d": 0,
            "fees24h": 0,
            "revenue24h": 0,
            "currentTvl": 0,
            "volumeHistory": {},
            "feesHistory": {},
            "revenueHistory": {},
            "tvlHistory": {},
        }

    # 1. Hyperliquid direct API
    print("\n--- Hyperliquid (direct API) ---")
    hl_data = fetch_hyperliquid_data()
    if hl_data:
        results["hyperliquid"].update({
            "volume24h": hl_data.get("volume24h", 0),
            "fees24h": hl_data.get("fees24h", 0),
            "revenue24h": hl_data.get("revenue24h", 0),
            "openInterest": hl_data.get("openInterest", 0),
            "source": "hyperliquid_api",
        })
        print(f"  Hyperliquid: ${hl_data.get('volume24h', 0):,.0f} 24h volume")
    else:
        print("  Hyperliquid direct API failed, will try CoinGecko fallback")

    # 2. dYdX direct API
    print("\n--- dYdX v4 (direct API) ---")
    dydx_data = fetch_dydx_data()
    if dydx_data:
        results["dydx"].update({
            "volume24h": dydx_data.get("volume24h", 0),
            "fees24h": dydx_data.get("fees24h", 0),
            "revenue24h": dydx_data.get("revenue24h", 0),
            "openInterest": dydx_data.get("openInterest", 0),
            "source": "dydx_indexer",
        })
        print(f"  dYdX: ${dydx_data.get('volume24h', 0):,.0f} 24h volume")
    else:
        print("  dYdX direct API failed, will try CoinGecko fallback")

    # 3. CoinGecko for remaining protocols
    print("\n--- CoinGecko (free tier) ---")
    cg_data = fetch_derivatives_exchanges()
    if cg_data:
        for slug, cg_proto in cg_data.items():
            if slug not in results:
                continue
            # Only use CoinGecko if we don't already have direct API data
            if results[slug].get("source"):
                continue
            results[slug].update({
                "volume24h": cg_proto.get("volume24h", 0),
                "fees24h": cg_proto.get("fees24h", 0),
                "revenue24h": cg_proto.get("revenue24h", 0),
                "openInterest": cg_proto.get("openInterest", 0),
                "source": "coingecko",
            })
            print(f"  {results[slug]['displayName']}: ${cg_proto.get('volume24h', 0):,.0f} 24h volume (CoinGecko)")
    else:
        print("  CoinGecko fetch failed")

    # 4. TVL from DefiLlama (still free and reliable)
    print("\n--- TVL (DefiLlama) ---")
    tvl_data = fetch_all_tvl()
    if tvl_data:
        for slug, tvl_info in tvl_data.items():
            if slug in results:
                results[slug]["tvlHistory"] = tvl_info.get("tvlHistory", {})
                results[slug]["currentTvl"] = tvl_info.get("currentTvl", 0)

    # 5. Merge with previous historical timeseries
    previous = load_previous_data("perps_latest.json")
    if previous:
        for slug, pdata in previous.items():
            if slug in results:
                # Preserve volume/fees/revenue history from previous runs
                for field in ("volumeHistory", "feesHistory", "revenueHistory"):
                    old_hist = pdata.get(field, {})
                    if old_hist and not results[slug].get(field):
                        results[slug][field] = old_hist

    return results


def fetch_all_options_data():
    """
    Fetch options data:
    1. Deribit direct API (~90% of crypto options volume)
    2. Previously saved data for smaller protocols

    Returns same structure as before: { overview: {}, protocols: {} }
    """
    print("\n=== Fetching Options Data ===")
    results = {}

    # Initialize all protocols
    for slug, name in OPTIONS_PROTOCOLS.items():
        results[slug] = {
            "displayName": name,
            "slug": slug,
            "volume24h": 0,
            "notionalVolume24h": 0,
            "premiumVolume24h": 0,
            "fees24h": 0,
            "revenue24h": 0,
            "volumeAllTime": 0,
            "volumeHistory": {},
            "feesHistory": {},
            "revenueHistory": {},
        }

    # 1. Deribit direct API
    print("\n--- Deribit (direct API) ---")
    deribit_data = fetch_deribit_options_data()
    if deribit_data:
        results["deribit"].update({
            "volume24h": deribit_data.get("volume24h", 0),
            "notionalVolume24h": deribit_data.get("notionalVolume24h", 0),
            "premiumVolume24h": deribit_data.get("premiumVolume24h", 0),
            "fees24h": deribit_data.get("fees24h", 0),
            "revenue24h": deribit_data.get("revenue24h", 0),
            "openInterest": deribit_data.get("openInterest", 0),
            "source": "deribit_api",
        })
        print(f"  Deribit: ${deribit_data.get('volume24h', 0):,.0f} 24h options volume")
    else:
        print("  Deribit direct API failed")

    # 2. Merge with previous data for history + smaller protocols
    previous = load_previous_data("options_latest.json")
    if previous:
        prev_protocols = previous.get("protocols", previous)
        for slug, pdata in prev_protocols.items():
            if slug in results:
                # Preserve historical timeseries
                for field in ("volumeHistory", "feesHistory", "revenueHistory"):
                    old_hist = pdata.get(field, {})
                    if old_hist and not results[slug].get(field):
                        results[slug][field] = old_hist
                # For non-Deribit protocols, keep last known values if no new data
                if slug != "deribit" and results[slug]["volume24h"] == 0:
                    for field in ("volume24h", "notionalVolume24h", "premiumVolume24h",
                                  "fees24h", "revenue24h", "volumeAllTime"):
                        if pdata.get(field):
                            results[slug][field] = pdata[field]

    # Build overview total history from preserved data
    overview_history = {}
    if previous and previous.get("overview", {}).get("totalHistory"):
        overview_history = previous["overview"]["totalHistory"]

    return {
        "overview": {"totalHistory": overview_history},
        "protocols": results,
    }


# ── Timeseries accumulation ───────────────────────────────────────────


def accumulate_daily_snapshot(history, perps_data, options_data):
    """
    Save today's volume/fees snapshot into history for building timeseries.
    This replaces DefiLlama's historical data with our own accumulation.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Perps daily snapshots: { slug: { date: volume } }
    perps_daily = history.get("perpsDaily", {})
    for slug, pdata in (perps_data or {}).items():
        vol = pdata.get("volume24h", 0) or 0
        if vol > 0:
            if slug not in perps_daily:
                perps_daily[slug] = {}
            perps_daily[slug][today] = vol
    history["perpsDaily"] = perps_daily

    # Options daily snapshots
    options_daily = history.get("optionsDaily", {})
    options_protocols = options_data.get("protocols", {}) if options_data else {}
    for slug, pdata in options_protocols.items():
        vol = pdata.get("volume24h", 0) or 0
        if vol > 0:
            if slug not in options_daily:
                options_daily[slug] = {}
            options_daily[slug][today] = vol
    history["optionsDaily"] = options_daily

    return history


def merge_timeseries(protocol_data, daily_history, slug):
    """
    Merge a protocol's existing volumeHistory with accumulated daily snapshots.
    The daily history (from our own accumulation) supplements the old DefiLlama data.
    """
    existing = dict(protocol_data.get("volumeHistory", {}))
    accumulated = daily_history.get(slug, {})

    # Accumulated data takes priority for dates where we have it
    existing.update(accumulated)
    protocol_data["volumeHistory"] = existing


# ── Dashboard data building (unchanged logic) ─────────────────────────


def _aggregate_volume_timeseries(protocols_data, top_n=6):
    """Build a unified timeseries from per-protocol volume history dicts."""
    all_dates = set()
    proto_volumes = {}
    for slug, pdata in protocols_data.items():
        hist = pdata.get("volumeHistory", {})
        if hist:
            all_dates.update(hist.keys())
            proto_volumes[pdata.get("displayName", slug)] = hist

    if not all_dates:
        return {"dates": [], "series": {}}

    dates = sorted(all_dates)
    ranked = sorted(
        proto_volumes.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True,
    )

    top_protos = [name for name, _ in ranked[:top_n]]
    others = [name for name, _ in ranked[top_n:]]

    series = {}
    for name in top_protos:
        series[name] = [proto_volumes[name].get(d, 0) for d in dates]

    if others:
        series["Others"] = [
            sum(proto_volumes[name].get(d, 0) for name in others)
            for d in dates
        ]

    return {"dates": dates, "series": series}


def _aggregate_fees_timeseries(protocols_data, field="feesHistory", top_n=6):
    """Build unified timeseries from per-protocol fees/revenue history."""
    all_dates = set()
    proto_fees = {}
    for slug, pdata in protocols_data.items():
        hist = pdata.get(field, {})
        if hist:
            all_dates.update(hist.keys())
            proto_fees[pdata.get("displayName", slug)] = hist

    if not all_dates:
        return {"dates": [], "series": {}}

    dates = sorted(all_dates)
    ranked = sorted(
        proto_fees.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True,
    )

    top_protos = [name for name, _ in ranked[:top_n]]
    others_names = [name for name, _ in ranked[top_n:]]

    series = {}
    for name in top_protos:
        series[name] = [proto_fees[name].get(d, 0) for d in dates]

    if others_names:
        series["Others"] = [
            sum(proto_fees[name].get(d, 0) for name in others_names)
            for d in dates
        ]

    return {"dates": dates, "series": series}


def _aggregate_tvl_timeseries(protocols_data, top_n=6):
    """Build unified TVL timeseries."""
    all_dates = set()
    proto_tvl = {}
    for slug, pdata in protocols_data.items():
        hist = pdata.get("tvlHistory", {})
        if hist:
            all_dates.update(hist.keys())
            proto_tvl[pdata.get("displayName", slug)] = hist

    if not all_dates:
        return {"dates": [], "series": {}}

    dates = sorted(all_dates)
    ranked = sorted(
        proto_tvl.items(),
        key=lambda x: max(x[1].values()) if x[1] else 0,
        reverse=True,
    )

    top_protos = [name for name, _ in ranked[:top_n]]
    others_names = [name for name, _ in ranked[top_n:]]

    series = {}
    for name in top_protos:
        series[name] = [proto_tvl[name].get(d, 0) for d in dates]

    if others_names:
        series["Others"] = [
            sum(proto_tvl[name].get(d, 0) for name in others_names)
            for d in dates
        ]

    return {"dates": dates, "series": series}


def _market_share(protocols_data, metric="volume24h"):
    """Calculate current market share by a given metric."""
    shares = {}
    for slug, pdata in protocols_data.items():
        name = pdata.get("displayName", slug)
        val = pdata.get(metric, 0) or 0
        if val > 0:
            shares[name] = val

    total = sum(shares.values())
    if total == 0:
        return {}

    return {name: round((val / total) * 100, 2) for name, val in
            sorted(shares.items(), key=lambda x: x[1], reverse=True)}


def _current_metrics(protocols_data):
    """Extract current snapshot metrics for summary cards."""
    total_vol_24h = sum((p.get("volume24h", 0) or 0) for p in protocols_data.values())
    total_fees_24h = sum((p.get("fees24h", 0) or 0) for p in protocols_data.values())
    total_revenue_24h = sum((p.get("revenue24h", 0) or 0) for p in protocols_data.values())
    total_tvl = sum((p.get("currentTvl", 0) or 0) for p in protocols_data.values())

    return {
        "volume24h": total_vol_24h,
        "fees24h": total_fees_24h,
        "revenue24h": total_revenue_24h,
        "tvl": total_tvl,
    }


def build_dashboard_data(perps_data, options_data, polymarket_data, kalshi_data):
    """Process raw data into the format needed by the dashboard."""
    now = datetime.now(timezone.utc).isoformat()

    # --- Perps ---
    perps_protocols = perps_data or {}
    perps_volume_ts = _aggregate_volume_timeseries(perps_protocols)
    perps_fees_ts = _aggregate_fees_timeseries(perps_protocols, "feesHistory")
    perps_revenue_ts = _aggregate_fees_timeseries(perps_protocols, "revenueHistory")
    perps_tvl_ts = _aggregate_tvl_timeseries(perps_protocols)
    perps_share = _market_share(perps_protocols, "volume24h")
    perps_metrics = _current_metrics(perps_protocols)

    # --- Options ---
    options_protocols = options_data.get("protocols", {}) if options_data else {}
    options_volume_ts = _aggregate_volume_timeseries(options_protocols)
    options_fees_ts = _aggregate_fees_timeseries(options_protocols, "feesHistory")
    options_revenue_ts = _aggregate_fees_timeseries(options_protocols, "revenueHistory")
    options_share = _market_share(options_protocols, "volume24h")
    options_metrics = _current_metrics(options_protocols)

    # Use overview total history if available
    options_total_history = {}
    if options_data and options_data.get("overview", {}).get("totalHistory"):
        options_total_history = options_data["overview"]["totalHistory"]

    # --- Prediction Markets ---
    poly = polymarket_data or {}
    kalshi_d = kalshi_data or {}

    predictions = {
        "polymarket": {
            "totalVolume": poly.get("totalVolume", {}).get("total", 0),
            "volume24h": poly.get("totalVolume", {}).get("volume24h", 0),
            "volume1w": poly.get("totalVolume", {}).get("volume1w", 0),
            "volume1m": poly.get("totalVolume", {}).get("volume1m", 0),
            "cryptoVolume": poly.get("cryptoVolume", {}).get("total", 0),
            "cryptoVolume24h": poly.get("cryptoVolume", {}).get("volume24h", 0),
            "pricePredictionPct": poly.get("pricePredictionPct", 0),
            "totalMarkets": poly.get("totalMarkets", 0),
            "cryptoMarkets": poly.get("cryptoMarkets", 0),
            "totalLiquidity": poly.get("totalLiquidity", 0),
            "cryptoLiquidity": poly.get("cryptoLiquidity", 0),
            "topCryptoMarkets": poly.get("topCryptoMarkets", []),
        },
        "kalshi": {
            "totalContracts": kalshi_d.get("totalStats", {}).get("totalContracts", 0),
            "contracts24h": kalshi_d.get("totalStats", {}).get("contracts24h", 0),
            "openInterest": kalshi_d.get("openStats", {}).get("openInterest", 0),
            "cryptoContracts": kalshi_d.get("cryptoStats", {}).get("totalContracts", 0),
            "cryptoContracts24h": kalshi_d.get("cryptoStats", {}).get("contracts24h", 0),
            "cryptoPct": kalshi_d.get("cryptoPct", 0),
            "pricePredictionPct": kalshi_d.get("pricePredictionPct", 0),
            "totalMarkets": kalshi_d.get("totalMarkets", 0),
            "cryptoMarkets": kalshi_d.get("cryptoMarkets", 0),
            "topCryptoMarkets": kalshi_d.get("topCryptoMarkets", []),
        },
    }

    # Build prediction market share
    pred_share = {}
    poly_vol = poly.get("totalVolume", {}).get("total", 0)
    kalshi_vol = kalshi_d.get("totalStats", {}).get("totalContracts", 0)
    pred_total = poly_vol + kalshi_vol
    if pred_total > 0:
        pred_share["Polymarket"] = round((poly_vol / pred_total) * 100, 2)
        pred_share["Kalshi"] = round((kalshi_vol / pred_total) * 100, 2)

    # --- Assemble final data ---
    dashboard_data = {
        "lastUpdated": now,
        "perps": {
            "metrics": perps_metrics,
            "volumeTimeseries": perps_volume_ts,
            "feesTimeseries": perps_fees_ts,
            "revenueTimeseries": perps_revenue_ts,
            "tvlTimeseries": perps_tvl_ts,
            "marketShare": perps_share,
            "protocols": {
                slug: {
                    "displayName": p.get("displayName", slug),
                    "volume24h": p.get("volume24h", 0),
                    "volume7d": p.get("volume7d", 0),
                    "volume30d": p.get("volume30d", 0),
                    "fees24h": p.get("fees24h", 0),
                    "revenue24h": p.get("revenue24h", 0),
                    "currentTvl": p.get("currentTvl", 0),
                    "volumeChange1d": p.get("volumeChange1d"),
                    "volumeChange7d": p.get("volumeChange7d"),
                    "volumeChange1m": p.get("volumeChange1m"),
                }
                for slug, p in perps_protocols.items()
            },
        },
        "options": {
            "metrics": options_metrics,
            "volumeTimeseries": options_volume_ts,
            "feesTimeseries": options_fees_ts,
            "revenueTimeseries": options_revenue_ts,
            "totalVolumeHistory": options_total_history,
            "marketShare": options_share,
            "protocols": {
                slug: {
                    "displayName": p.get("displayName", slug),
                    "volume24h": p.get("volume24h", 0),
                    "notionalVolume24h": p.get("notionalVolume24h", 0),
                    "premiumVolume24h": p.get("premiumVolume24h", 0),
                    "fees24h": p.get("fees24h", 0),
                    "revenue24h": p.get("revenue24h", 0),
                    "volumeAllTime": p.get("volumeAllTime", 0),
                }
                for slug, p in options_protocols.items()
            },
        },
        "predictions": predictions,
        "predictionMarketShare": pred_share,
    }

    return dashboard_data


def save_prediction_snapshot(history, polymarket_data, kalshi_data):
    """Append a daily snapshot for prediction market historical tracking."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshots = history.get("predictionHistory", [])

    # Don't duplicate today's entry
    if snapshots and snapshots[-1].get("date") == today:
        snapshots.pop()

    poly = polymarket_data or {}
    kalshi_d = kalshi_data or {}

    snapshots.append({
        "date": today,
        "polymarket": {
            "totalVolume": poly.get("totalVolume", {}).get("total", 0),
            "cryptoVolume": poly.get("cryptoVolume", {}).get("total", 0),
            "pricePredictionPct": poly.get("pricePredictionPct", 0),
            "totalLiquidity": poly.get("totalLiquidity", 0),
        },
        "kalshi": {
            "totalContracts": kalshi_d.get("totalStats", {}).get("totalContracts", 0),
            "cryptoContracts": kalshi_d.get("cryptoStats", {}).get("totalContracts", 0),
            "pricePredictionPct": kalshi_d.get("pricePredictionPct", 0),
        },
    })

    history["predictionHistory"] = snapshots
    return history


def generate_dashboard_js(dashboard_data, prediction_history):
    """Write the dashboard data as a JavaScript file for the frontend."""
    dashboard_data["predictionHistory"] = prediction_history

    js_content = (
        "// Auto-generated by update_data.py — do not edit manually\n"
        f"// Last updated: {dashboard_data['lastUpdated']}\n"
        f"const DASHBOARD_DATA = {json.dumps(dashboard_data, indent=2)};\n"
    )

    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    output_path = os.path.join(DASHBOARD_DIR, "data.js")
    with open(output_path, "w") as f:
        f.write(js_content)
    print(f"\nDashboard data written to {output_path}")


def main():
    start = time.time()
    print(f"{'='*60}")
    print(f"Crypto Derivatives Market Intelligence - Data Update")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Sources: Hyperliquid, dYdX, Deribit, CoinGecko, DefiLlama (TVL)")
    print(f"{'='*60}")

    # Load existing history
    history = load_history()

    # Fetch all data
    perps_data = fetch_all_perps_data()
    options_data = fetch_all_options_data()
    polymarket_data = fetch_all_polymarket_data()
    kalshi_data = fetch_all_kalshi_data()

    # Accumulate daily volume snapshots into history
    history = accumulate_daily_snapshot(history, perps_data, options_data)

    # Merge accumulated history back into protocol data for timeseries
    for slug in perps_data:
        merge_timeseries(perps_data[slug], history.get("perpsDaily", {}), slug)
    for slug in options_data.get("protocols", {}):
        merge_timeseries(options_data["protocols"][slug], history.get("optionsDaily", {}), slug)

    # Save raw data snapshots
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "perps_latest.json"), "w") as f:
        json.dump(perps_data, f, indent=2)
    with open(os.path.join(DATA_DIR, "options_latest.json"), "w") as f:
        json.dump(options_data, f, indent=2)
    with open(os.path.join(DATA_DIR, "polymarket_latest.json"), "w") as f:
        json.dump(polymarket_data, f, indent=2)
    with open(os.path.join(DATA_DIR, "kalshi_latest.json"), "w") as f:
        json.dump(kalshi_data, f, indent=2)
    print("\nRaw data saved to data/ directory")

    # Save prediction history
    history = save_prediction_snapshot(history, polymarket_data, kalshi_data)
    save_history(history)

    # Build dashboard data
    dashboard_data = build_dashboard_data(perps_data, options_data, polymarket_data, kalshi_data)

    # Generate JS data file
    generate_dashboard_js(dashboard_data, history.get("predictionHistory", []))

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Update complete in {elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
