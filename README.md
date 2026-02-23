# Crypto Derivatives Market Intelligence Dashboard

Tracks the growth of crypto options, perpetuals, and prediction markets — volume, liquidity, revenue, and market share over time.

## Categories Tracked

### Perpetuals (Perps)
Hyperliquid, Lighter, dYdX, GMX, Vertex, Jupiter Perps, Drift, Aevo, Gains Network, Bluefin

### Options
Deribit, Aevo, Derive, Premia, Moby, Stryke, Typus, Ithaca

### Prediction Markets
Polymarket, Kalshi — with breakdown of crypto/price prediction volume vs total

## Quick Start

```bash
pip install -r requirements.txt

# Fetch live data (requires internet)
python update_data.py

# Open dashboard
open dashboard/index.html
# or
python -m http.server 8000 --directory dashboard
```

## Daily Updates

Run once per day to refresh all data:

```bash
python update_data.py
```

Or set up a cron job:

```bash
# Run daily at 6 AM UTC
0 6 * * * cd /path/to/options-market-intelligence && python update_data.py
```

## Data Sources

| Source | Data | API |
|--------|------|-----|
| [DefiLlama](https://defillama.com) | Perps volume, options volume, fees, revenue, TVL | Free REST API |
| [Polymarket](https://polymarket.com) | Prediction market volume, crypto markets | Gamma API |
| [Kalshi](https://kalshi.com) | Prediction market volume, crypto markets | Trade API v2 |
| Hyperliquid | Perps volume, OI, funding | REST API |
| Deribit | Options volume, OI | Public API v2 |

## Project Structure

```
├── dashboard/
│   ├── index.html          # Main dashboard page
│   ├── styles.css           # Dark theme styling
│   ├── app.js               # Chart.js rendering logic
│   └── data.js              # Generated data (auto-created by update scripts)
├── collectors/
│   ├── __init__.py          # Shared HTTP utilities
│   ├── defillama.py         # DefiLlama API (perps, options, fees)
│   ├── polymarket.py        # Polymarket Gamma API
│   └── kalshi.py            # Kalshi Trade API
├── data/                    # Raw data snapshots
├── update_data.py           # Main update script (fetches live data)
├── generate_sample_data.py  # Generate sample data for demo
└── requirements.txt
```

## Dashboard Features

- **Overview**: Summary metrics + combined volume charts
- **Perpetuals**: Volume, fees, revenue, TVL over time with protocol breakdown
- **Options**: Volume, fees, revenue over time with protocol breakdown
- **Prediction Markets**: Volume breakdown, crypto vs total, price prediction percentages
- **Time filters**: 30D, 90D, 1Y, All on each chart
- **Market share**: Doughnut charts showing current competitive landscape
- **Protocol tables**: Sortable metrics per protocol
