#!/usr/bin/env python3
"""
Daily data updater for the crypto derivatives market intelligence dashboard.

Usage:
    python update_data.py

Run once daily to fetch fresh data from all sources and regenerate the dashboard.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

from collectors.defillama import fetch_all_perps_data, fetch_all_options_data
from collectors.polymarket import fetch_all_polymarket_data
from collectors.kalshi import fetch_all_kalshi_data

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def load_history():
    """Load existing historical snapshots."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"snapshots": [], "predictionHistory": []}


def save_history(history):
    """Save historical snapshots."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _aggregate_volume_timeseries(protocols_data, top_n=6):
    """
    Build a unified timeseries from per-protocol volume history dicts.
    Returns { dates: [...], series: { "Proto": [...], ... } }
    Groups smaller protocols into "Others".
    """
    # Collect all dates
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

    # Rank protocols by total volume
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
        others_series = []
        for d in dates:
            others_series.append(sum(proto_volumes[name].get(d, 0) for name in others))
        series["Others"] = others_series

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

    # Build prediction market share (by total volume - approximate)
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
    # Include prediction history in the data
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
    print(f"{'='*60}")

    # Load existing history
    history = load_history()

    # Fetch all data
    perps_data = fetch_all_perps_data()
    options_data = fetch_all_options_data()
    polymarket_data = fetch_all_polymarket_data()
    kalshi_data = fetch_all_kalshi_data()

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
