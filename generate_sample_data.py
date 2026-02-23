#!/usr/bin/env python3
"""
Generate realistic sample data for dashboard development and demonstration.

This creates a data.js file with plausible market data based on publicly
known figures for major crypto derivatives protocols.

Run the real update_data.py when you have internet access to replace
this with live data.
"""

import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

random.seed(42)  # Reproducible


def date_range(start_date, end_date):
    """Generate YYYY-MM-DD strings for a date range."""
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return dates


def growth_curve(n, base, peak, growth_start=0.3, noise=0.15):
    """
    Generate a growth curve with noise.
    Starts slow, accelerates, with random daily variation.
    """
    vals = []
    for i in range(n):
        t = i / max(n - 1, 1)
        # S-curve growth
        if t < growth_start:
            pct = (t / growth_start) * 0.1
        else:
            pct = 0.1 + 0.9 * ((t - growth_start) / (1 - growth_start)) ** 1.5
        val = base + (peak - base) * pct
        # Add noise
        val *= 1 + random.gauss(0, noise)
        # Add weekly seasonality (lower weekends)
        day_of_week = i % 7
        if day_of_week >= 5:
            val *= 0.7
        vals.append(max(0, val))
    return vals


def spike_growth(n, base, peak, spike_points=None, noise=0.2):
    """Growth with occasional spikes (market events)."""
    vals = growth_curve(n, base, peak, noise=noise)
    if spike_points:
        for sp, mult in spike_points:
            idx = int(sp * n)
            for j in range(max(0, idx - 3), min(n, idx + 5)):
                dist = abs(j - idx)
                vals[j] *= 1 + (mult - 1) * max(0, 1 - dist / 5)
    return vals


def main():
    end_date = datetime(2026, 2, 23)
    start_date = datetime(2023, 1, 1)
    dates = date_range(start_date, end_date)
    n = len(dates)

    # Last 365 days for recent data
    recent_start = n - 365 if n > 365 else 0

    # ═══════════════════════════════════════════════════════════════
    # PERPS DATA
    # ═══════════════════════════════════════════════════════════════
    # Based on known market data:
    # - Hyperliquid: dominant player, ~$5-15B daily volume in 2025-2026
    # - dYdX: ~$500M-2B daily
    # - GMX: ~$200M-800M daily
    # - Lighter: newer, growing, ~$50M-500M
    # - Others: various ranges

    perps_protocols = {
        "hyperliquid": {
            "displayName": "Hyperliquid",
            "base_vol": 500e6, "peak_vol": 12e9,
            "base_fee": 200e3, "peak_fee": 4.5e6,
            "base_rev": 100e3, "peak_rev": 2.5e6,
            "base_tvl": 100e6, "peak_tvl": 3.5e9,
            "growth_start": 0.4,
        },
        "lighter-v2": {
            "displayName": "Lighter",
            "base_vol": 0, "peak_vol": 800e6,
            "base_fee": 0, "peak_fee": 300e3,
            "base_rev": 0, "peak_rev": 150e3,
            "base_tvl": 0, "peak_tvl": 200e6,
            "growth_start": 0.7,
        },
        "dydx": {
            "displayName": "dYdX",
            "base_vol": 800e6, "peak_vol": 1.5e9,
            "base_fee": 300e3, "peak_fee": 600e3,
            "base_rev": 200e3, "peak_rev": 400e3,
            "base_tvl": 300e6, "peak_tvl": 500e6,
            "growth_start": 0.1,
        },
        "gmx-v2": {
            "displayName": "GMX",
            "base_vol": 200e6, "peak_vol": 600e6,
            "base_fee": 200e3, "peak_fee": 500e3,
            "base_rev": 100e3, "peak_rev": 300e3,
            "base_tvl": 400e6, "peak_tvl": 700e6,
            "growth_start": 0.1,
        },
        "vertex-protocol": {
            "displayName": "Vertex",
            "base_vol": 50e6, "peak_vol": 1.2e9,
            "base_fee": 20e3, "peak_fee": 400e3,
            "base_rev": 10e3, "peak_rev": 200e3,
            "base_tvl": 20e6, "peak_tvl": 300e6,
            "growth_start": 0.3,
        },
        "jupiter-perpetual": {
            "displayName": "Jupiter Perps",
            "base_vol": 0, "peak_vol": 2e9,
            "base_fee": 0, "peak_fee": 800e3,
            "base_rev": 0, "peak_rev": 500e3,
            "base_tvl": 0, "peak_tvl": 800e6,
            "growth_start": 0.5,
        },
        "drift-protocol": {
            "displayName": "Drift",
            "base_vol": 30e6, "peak_vol": 500e6,
            "base_fee": 10e3, "peak_fee": 200e3,
            "base_rev": 5e3, "peak_rev": 100e3,
            "base_tvl": 20e6, "peak_tvl": 250e6,
            "growth_start": 0.3,
        },
        "aevo": {
            "displayName": "Aevo",
            "base_vol": 0, "peak_vol": 400e6,
            "base_fee": 0, "peak_fee": 150e3,
            "base_rev": 0, "peak_rev": 80e3,
            "base_tvl": 0, "peak_tvl": 150e6,
            "growth_start": 0.5,
        },
        "gains-network": {
            "displayName": "Gains Network",
            "base_vol": 50e6, "peak_vol": 300e6,
            "base_fee": 30e3, "peak_fee": 150e3,
            "base_rev": 15e3, "peak_rev": 80e3,
            "base_tvl": 30e6, "peak_tvl": 120e6,
            "growth_start": 0.1,
        },
        "bluefin": {
            "displayName": "Bluefin",
            "base_vol": 0, "peak_vol": 600e6,
            "base_fee": 0, "peak_fee": 200e3,
            "base_rev": 0, "peak_rev": 100e3,
            "base_tvl": 0, "peak_tvl": 180e6,
            "growth_start": 0.6,
        },
    }

    spike_events = [(0.45, 2.5), (0.6, 1.8), (0.75, 3.0), (0.88, 2.2), (0.95, 1.5)]

    perps_volume_series = {}
    perps_fees_series = {}
    perps_revenue_series = {}
    perps_tvl_series = {}
    perps_proto_info = {}

    for slug, cfg in perps_protocols.items():
        vol = spike_growth(n, cfg["base_vol"], cfg["peak_vol"], spike_events, noise=0.2)
        fee = spike_growth(n, cfg["base_fee"], cfg["peak_fee"], spike_events, noise=0.2)
        rev = spike_growth(n, cfg["base_rev"], cfg["peak_rev"], spike_events, noise=0.2)
        tvl = growth_curve(n, cfg["base_tvl"], cfg["peak_tvl"], cfg["growth_start"], noise=0.05)

        # Zero out early data for newer protocols
        gs = cfg["growth_start"]
        zero_until = int(gs * n * 0.8)
        for i in range(zero_until):
            vol[i] = 0
            fee[i] = 0
            rev[i] = 0
            tvl[i] = 0

        perps_volume_series[cfg["displayName"]] = [round(v) for v in vol]
        perps_fees_series[cfg["displayName"]] = [round(v) for v in fee]
        perps_revenue_series[cfg["displayName"]] = [round(v) for v in rev]
        perps_tvl_series[cfg["displayName"]] = [round(v) for v in tvl]

        # Current metrics (last day)
        perps_proto_info[slug] = {
            "displayName": cfg["displayName"],
            "volume24h": round(vol[-1]),
            "volume7d": round(sum(vol[-7:])),
            "volume30d": round(sum(vol[-30:])),
            "fees24h": round(fee[-1]),
            "revenue24h": round(rev[-1]),
            "currentTvl": round(tvl[-1]),
            "volumeChange1d": round((vol[-1] / max(vol[-2], 1) - 1) * 100, 1),
            "volumeChange7d": round((sum(vol[-7:]) / max(sum(vol[-14:-7]), 1) - 1) * 100, 1),
            "volumeChange1m": round((sum(vol[-30:]) / max(sum(vol[-60:-30]), 1) - 1) * 100, 1),
        }

    # Compute market share
    total_vol_24h = sum(p["volume24h"] for p in perps_proto_info.values())
    perps_market_share = {}
    for slug, p in perps_proto_info.items():
        if p["volume24h"] > 0:
            perps_market_share[p["displayName"]] = round((p["volume24h"] / total_vol_24h) * 100, 2)

    perps_metrics = {
        "volume24h": total_vol_24h,
        "fees24h": sum(p["fees24h"] for p in perps_proto_info.values()),
        "revenue24h": sum(p["revenue24h"] for p in perps_proto_info.values()),
        "tvl": sum(p["currentTvl"] for p in perps_proto_info.values()),
    }

    # ═══════════════════════════════════════════════════════════════
    # OPTIONS DATA
    # ═══════════════════════════════════════════════════════════════
    options_protocols = {
        "deribit": {
            "displayName": "Deribit",
            "base_vol": 500e6, "peak_vol": 4e9,
            "base_fee": 200e3, "peak_fee": 1.5e6,
            "base_rev": 150e3, "peak_rev": 1.2e6,
            "growth_start": 0.1,
        },
        "aevo": {
            "displayName": "Aevo",
            "base_vol": 0, "peak_vol": 200e6,
            "base_fee": 0, "peak_fee": 80e3,
            "base_rev": 0, "peak_rev": 50e3,
            "growth_start": 0.5,
        },
        "derive": {
            "displayName": "Derive",
            "base_vol": 10e6, "peak_vol": 150e6,
            "base_fee": 5e3, "peak_fee": 60e3,
            "base_rev": 3e3, "peak_rev": 40e3,
            "growth_start": 0.3,
        },
        "premia": {
            "displayName": "Premia",
            "base_vol": 5e6, "peak_vol": 80e6,
            "base_fee": 3e3, "peak_fee": 30e3,
            "base_rev": 2e3, "peak_rev": 20e3,
            "growth_start": 0.2,
        },
        "moby": {
            "displayName": "Moby",
            "base_vol": 0, "peak_vol": 100e6,
            "base_fee": 0, "peak_fee": 40e3,
            "base_rev": 0, "peak_rev": 25e3,
            "growth_start": 0.6,
        },
        "stryke": {
            "displayName": "Stryke",
            "base_vol": 0, "peak_vol": 50e6,
            "base_fee": 0, "peak_fee": 20e3,
            "base_rev": 0, "peak_rev": 12e3,
            "growth_start": 0.55,
        },
        "typus-finance": {
            "displayName": "Typus",
            "base_vol": 0, "peak_vol": 60e6,
            "base_fee": 0, "peak_fee": 25e3,
            "base_rev": 0, "peak_rev": 15e3,
            "growth_start": 0.5,
        },
        "ithaca-protocol": {
            "displayName": "Ithaca",
            "base_vol": 0, "peak_vol": 40e6,
            "base_fee": 0, "peak_fee": 15e3,
            "base_rev": 0, "peak_rev": 10e3,
            "growth_start": 0.65,
        },
    }

    options_volume_series = {}
    options_fees_series = {}
    options_revenue_series = {}
    options_proto_info = {}

    for slug, cfg in options_protocols.items():
        vol = spike_growth(n, cfg["base_vol"], cfg["peak_vol"], spike_events, noise=0.25)
        fee = spike_growth(n, cfg["base_fee"], cfg["peak_fee"], spike_events, noise=0.25)
        rev = spike_growth(n, cfg["base_rev"], cfg["peak_rev"], spike_events, noise=0.25)

        gs = cfg["growth_start"]
        zero_until = int(gs * n * 0.8)
        for i in range(zero_until):
            vol[i] = 0
            fee[i] = 0
            rev[i] = 0

        options_volume_series[cfg["displayName"]] = [round(v) for v in vol]
        options_fees_series[cfg["displayName"]] = [round(v) for v in fee]
        options_revenue_series[cfg["displayName"]] = [round(v) for v in rev]

        options_proto_info[slug] = {
            "displayName": cfg["displayName"],
            "volume24h": round(vol[-1]),
            "notionalVolume24h": round(vol[-1] * 1.2),
            "premiumVolume24h": round(vol[-1] * 0.03),
            "fees24h": round(fee[-1]),
            "revenue24h": round(rev[-1]),
            "volumeAllTime": round(sum(vol)),
        }

    total_opt_vol_24h = sum(p["volume24h"] for p in options_proto_info.values())
    options_market_share = {}
    for slug, p in options_proto_info.items():
        if p["volume24h"] > 0:
            options_market_share[p["displayName"]] = round((p["volume24h"] / total_opt_vol_24h) * 100, 2)

    options_metrics = {
        "volume24h": total_opt_vol_24h,
        "fees24h": sum(p["fees24h"] for p in options_proto_info.values()),
        "revenue24h": sum(p["revenue24h"] for p in options_proto_info.values()),
        "tvl": 0,
    }

    # ═══════════════════════════════════════════════════════════════
    # PREDICTION MARKETS
    # ═══════════════════════════════════════════════════════════════
    # Polymarket: ~$10B+ total volume, crypto is ~15-25% of total
    poly_total_vol = 12.5e9
    poly_crypto_vol = 2.8e9
    poly_crypto_pct = round((poly_crypto_vol / poly_total_vol) * 100, 2)

    poly_top_crypto = [
        {"question": "Will Bitcoin be above $100,000 on March 31?", "volume": 450e6, "volume24h": 12e6, "liquidity": 8e6, "closed": False},
        {"question": "Will Ethereum reach $5,000 before April?", "volume": 320e6, "volume24h": 8.5e6, "liquidity": 5e6, "closed": False},
        {"question": "Bitcoin price end of Q1 2026", "volume": 280e6, "volume24h": 7e6, "liquidity": 4.5e6, "closed": False},
        {"question": "Will Solana be above $200 on March 31?", "volume": 180e6, "volume24h": 5e6, "liquidity": 3e6, "closed": False},
        {"question": "Bitcoin above $120,000 by June 2026?", "volume": 150e6, "volume24h": 4e6, "liquidity": 3.5e6, "closed": False},
        {"question": "Will ETH flip 0.05 BTC ratio?", "volume": 95e6, "volume24h": 2.5e6, "liquidity": 1.8e6, "closed": False},
        {"question": "Ethereum above $4,000 by March?", "volume": 88e6, "volume24h": 3e6, "liquidity": 2e6, "closed": False},
        {"question": "Will XRP be above $3 on April 1?", "volume": 65e6, "volume24h": 1.8e6, "liquidity": 1.2e6, "closed": False},
        {"question": "Bitcoin all-time high in Q1 2026?", "volume": 55e6, "volume24h": 1.5e6, "liquidity": 1e6, "closed": False},
        {"question": "Will DOGE reach $0.50?", "volume": 42e6, "volume24h": 1.2e6, "liquidity": 0.8e6, "closed": False},
    ]

    # Kalshi: regulated, smaller crypto, more politics/weather
    kalshi_total = 85e6  # contracts
    kalshi_crypto = 4.2e6
    kalshi_crypto_pct = round((kalshi_crypto / kalshi_total) * 100, 2)
    kalshi_price_pred = 3.5e6
    kalshi_price_pct = round((kalshi_price_pred / kalshi_total) * 100, 2)

    kalshi_top_crypto = [
        {"title": "Bitcoin above $100K", "subtitle": "on March 31", "volume": 850000, "volume24h": 25000, "openInterest": 120000, "isPricePrediction": True},
        {"title": "Ethereum above $4,000", "subtitle": "end of March", "volume": 620000, "volume24h": 18000, "openInterest": 85000, "isPricePrediction": True},
        {"title": "Bitcoin above $120K", "subtitle": "by June 30", "volume": 450000, "volume24h": 12000, "openInterest": 65000, "isPricePrediction": True},
        {"title": "Solana above $200", "subtitle": "end of Q1", "volume": 320000, "volume24h": 9000, "openInterest": 42000, "isPricePrediction": True},
        {"title": "Bitcoin above $80K", "subtitle": "March 31", "volume": 280000, "volume24h": 5000, "openInterest": 35000, "isPricePrediction": True},
        {"title": "Crypto total market cap", "subtitle": "above $4T", "volume": 180000, "volume24h": 4500, "openInterest": 28000, "isPricePrediction": False},
        {"title": "Bitcoin above $150K", "subtitle": "by Dec 2026", "volume": 150000, "volume24h": 3800, "openInterest": 22000, "isPricePrediction": True},
        {"title": "XRP above $3", "subtitle": "by March 31", "volume": 95000, "volume24h": 2200, "openInterest": 15000, "isPricePrediction": True},
    ]

    # Prediction market history (daily snapshots for the last 90 days)
    pred_history = []
    pred_dates = date_range(end_date - timedelta(days=89), end_date)
    for i, d in enumerate(pred_dates):
        t = i / len(pred_dates)
        poly_snap_total = poly_total_vol * (0.85 + 0.15 * t) * (1 + random.gauss(0, 0.02))
        poly_snap_crypto = poly_crypto_vol * (0.8 + 0.2 * t) * (1 + random.gauss(0, 0.03))
        kalshi_snap_total = kalshi_total * (0.9 + 0.1 * t) * (1 + random.gauss(0, 0.02))
        kalshi_snap_crypto = kalshi_crypto * (0.85 + 0.15 * t) * (1 + random.gauss(0, 0.03))

        pred_history.append({
            "date": d,
            "polymarket": {
                "totalVolume": round(poly_snap_total),
                "cryptoVolume": round(poly_snap_crypto),
                "pricePredictionPct": round(poly_snap_crypto / poly_snap_total * 100, 2),
                "totalLiquidity": round(350e6 * (0.9 + 0.1 * t)),
            },
            "kalshi": {
                "totalContracts": round(kalshi_snap_total),
                "cryptoContracts": round(kalshi_snap_crypto),
                "pricePredictionPct": round(kalshi_price_pct * (0.95 + 0.05 * t), 2),
            },
        })

    # ═══════════════════════════════════════════════════════════════
    # ASSEMBLE DASHBOARD DATA
    # ═══════════════════════════════════════════════════════════════
    pred_total = poly_total_vol + kalshi_total
    pred_market_share = {
        "Polymarket": round((poly_total_vol / pred_total) * 100, 2),
        "Kalshi": round((kalshi_total / pred_total) * 100, 2),
    }

    dashboard_data = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "perps": {
            "metrics": perps_metrics,
            "volumeTimeseries": {"dates": dates, "series": perps_volume_series},
            "feesTimeseries": {"dates": dates, "series": perps_fees_series},
            "revenueTimeseries": {"dates": dates, "series": perps_revenue_series},
            "tvlTimeseries": {"dates": dates, "series": perps_tvl_series},
            "marketShare": perps_market_share,
            "protocols": perps_proto_info,
        },
        "options": {
            "metrics": options_metrics,
            "volumeTimeseries": {"dates": dates, "series": options_volume_series},
            "feesTimeseries": {"dates": dates, "series": options_fees_series},
            "revenueTimeseries": {"dates": dates, "series": options_revenue_series},
            "totalVolumeHistory": {},
            "marketShare": options_market_share,
            "protocols": options_proto_info,
        },
        "predictions": {
            "polymarket": {
                "totalVolume": poly_total_vol,
                "volume24h": 85e6,
                "volume1w": 580e6,
                "volume1m": 2.1e9,
                "cryptoVolume": poly_crypto_vol,
                "cryptoVolume24h": 18e6,
                "pricePredictionPct": poly_crypto_pct,
                "totalMarkets": 1250,
                "cryptoMarkets": 185,
                "totalLiquidity": 380e6,
                "cryptoLiquidity": 65e6,
                "topCryptoMarkets": poly_top_crypto,
            },
            "kalshi": {
                "totalContracts": int(kalshi_total),
                "contracts24h": 280000,
                "openInterest": 1200000,
                "cryptoContracts": int(kalshi_crypto),
                "cryptoContracts24h": 15000,
                "cryptoPct": kalshi_crypto_pct,
                "pricePredictionPct": kalshi_price_pct,
                "totalMarkets": 3200,
                "cryptoMarkets": 95,
                "pricePredictionMarkets": 68,
                "topCryptoMarkets": kalshi_top_crypto,
            },
        },
        "predictionMarketShare": pred_market_share,
        "predictionHistory": pred_history,
    }

    # Write data.js
    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    js_content = (
        "// Auto-generated by generate_sample_data.py — sample data for demonstration\n"
        f"// Generated: {dashboard_data['lastUpdated']}\n"
        "// Run `python update_data.py` with internet access to fetch live data\n"
        f"const DASHBOARD_DATA = {json.dumps(dashboard_data)};\n"
    )
    output_path = os.path.join(DASHBOARD_DIR, "data.js")
    with open(output_path, "w") as f:
        f.write(js_content)
    print(f"Sample data written to {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

    # Also save history.json
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "history.json"), "w") as f:
        json.dump({"snapshots": [], "predictionHistory": pred_history}, f)
    print("History saved to data/history.json")


if __name__ == "__main__":
    main()
