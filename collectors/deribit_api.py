"""
Deribit public API collector for options data.

Free, no API key required for public endpoints.
Base URL: https://www.deribit.com/api/v2/public/
Docs: https://docs.deribit.com/

Deribit dominates crypto options (~90%+ of market volume).
"""

from collectors import api_get

BASE_URL = "https://www.deribit.com/api/v2/public"

# Deribit fee rates
OPTIONS_FEE_RATE = 0.0003  # 0.03% of underlying for options
REVENUE_SHARE = 0.7  # Deribit keeps most fees (centralized)


def _fetch_book_summaries(currency, kind="option"):
    """Fetch book summaries for all instruments of a given currency and kind."""
    data = api_get(
        f"{BASE_URL}/get_book_summary_by_currency",
        params={"currency": currency, "kind": kind},
    )
    if not data:
        return []
    return data.get("result", [])


def _fetch_index_price(currency):
    """Fetch current index price for a currency."""
    data = api_get(
        f"{BASE_URL}/get_index_price",
        params={"index_name": f"{currency.lower()}_usd"},
    )
    if not data:
        return 0
    return data.get("result", {}).get("index_price", 0)


def _aggregate_options(summaries, index_price):
    """Aggregate options data from book summaries."""
    total_volume_usd = 0
    total_oi_usd = 0
    total_oi_contracts = 0
    instrument_count = 0

    for inst in summaries:
        # Volume and OI are in base currency (BTC/ETH)
        volume = float(inst.get("volume", 0) or 0)
        oi = float(inst.get("open_interest", 0) or 0)

        total_volume_usd += volume * index_price
        total_oi_usd += oi * index_price
        total_oi_contracts += oi
        instrument_count += 1

    return {
        "volumeUsd": total_volume_usd,
        "openInterestUsd": total_oi_usd,
        "openInterestContracts": total_oi_contracts,
        "instrumentCount": instrument_count,
    }


def _aggregate_futures(summaries, index_price):
    """Aggregate futures/perps data from book summaries."""
    total_volume_usd = 0
    total_oi_usd = 0

    for inst in summaries:
        volume = float(inst.get("volume", 0) or 0)
        oi = float(inst.get("open_interest", 0) or 0)

        total_volume_usd += volume * index_price
        total_oi_usd += oi * index_price

    return {
        "volumeUsd": total_volume_usd,
        "openInterestUsd": total_oi_usd,
    }


def fetch_deribit_options_data():
    """Fetch aggregated options data from Deribit for BTC and ETH."""
    print("  Fetching Deribit options data (direct API)...")

    total_options_volume = 0
    total_options_oi = 0
    total_options_contracts = 0
    total_instruments = 0
    currency_breakdown = {}

    for currency in ["BTC", "ETH"]:
        print(f"    Fetching {currency} options...")
        index_price = _fetch_index_price(currency)
        if not index_price:
            print(f"    Could not get {currency} index price, skipping")
            continue

        summaries = _fetch_book_summaries(currency, "option")
        if not summaries:
            print(f"    No {currency} option summaries returned")
            continue

        agg = _aggregate_options(summaries, index_price)
        total_options_volume += agg["volumeUsd"]
        total_options_oi += agg["openInterestUsd"]
        total_options_contracts += agg["openInterestContracts"]
        total_instruments += agg["instrumentCount"]

        currency_breakdown[currency] = {
            "indexPrice": index_price,
            "volume24hUsd": agg["volumeUsd"],
            "openInterestUsd": agg["openInterestUsd"],
            "instrumentCount": agg["instrumentCount"],
        }

    # Estimate fees
    fees_24h = total_options_volume * OPTIONS_FEE_RATE
    revenue_24h = fees_24h * REVENUE_SHARE

    return {
        "displayName": "Deribit",
        "slug": "deribit",
        "volume24h": total_options_volume,
        "notionalVolume24h": total_options_volume,
        "premiumVolume24h": 0,  # Would need per-instrument premium calc
        "openInterest": total_options_oi,
        "openInterestContracts": total_options_contracts,
        "fees24h": fees_24h,
        "revenue24h": revenue_24h,
        "instrumentCount": total_instruments,
        "currencyBreakdown": currency_breakdown,
    }


def fetch_deribit_futures_data():
    """Fetch aggregated futures/perps data from Deribit."""
    print("  Fetching Deribit futures data (direct API)...")

    total_volume = 0
    total_oi = 0

    for currency in ["BTC", "ETH"]:
        index_price = _fetch_index_price(currency)
        if not index_price:
            continue

        for kind in ["future", "future_combo"]:
            summaries = _fetch_book_summaries(currency, kind)
            if summaries:
                agg = _aggregate_futures(summaries, index_price)
                total_volume += agg["volumeUsd"]
                total_oi += agg["openInterestUsd"]

    return {
        "displayName": "Deribit",
        "slug": "deribit",
        "volume24h": total_volume,
        "openInterest": total_oi,
    }


def fetch_deribit_volatility():
    """Fetch DVOL (Deribit Volatility Index) for BTC and ETH."""
    print("  Fetching Deribit volatility indices...")
    result = {}

    for currency in ["BTC", "ETH"]:
        data = api_get(
            f"{BASE_URL}/get_volatility_index_data",
            params={"currency": currency, "resolution": "1D", "start_timestamp": 0,
                    "end_timestamp": 9999999999999},
        )
        if data and data.get("result"):
            # Returns array of [timestamp, open, high, low, close]
            points = data["result"].get("data", [])
            if points:
                latest = points[-1]
                result[currency] = {
                    "dvol": latest[4] if len(latest) > 4 else None,  # close
                    "high": latest[2] if len(latest) > 2 else None,
                    "low": latest[3] if len(latest) > 3 else None,
                }

    return result
