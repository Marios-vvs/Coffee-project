# ☕ Coffee Machine Arbitrage Tracker

Monitors UK auction sites for premium coffee equipment deals, matches them against a reference price database, calculates arbitrage potential, and exports results to a formatted Excel workbook.

## How It Works

1. **Scrape** — Playwright-powered headless browser searches 7 UK auction sites for coffee equipment
2. **Match** — Listing titles are matched against 80+ premium machines (La Marzocco, Sage, Rocket, ECM, Jura, Mazzer, etc.)
3. **Calculate** — Arbitrage metrics: discount %, gross potential, conservative resale estimate, net profit
4. **Export** — Colour-coded Excel workbook with deal ratings (🔥 Strong Buy / ✅ Good Deal / ⚠️ Fair / ❌ Overpriced)

## Auction Sources

| Site | Type | Best For |
|------|------|----------|
| John Pye | Timed online | Retail returns, ex-display |
| i-bidder | Aggregator | Hundreds of UK auction houses |
| Bidspotter | Commercial | Café closures, restaurant liquidation |
| BPI Auctions | Specialist | Catering/industrial liquidation |
| Pro Auction | Specialist | London/SE café clearances |
| Wilsons Auctions | General | Government surplus, police seizures |
| Auction News | Meta-source | Upcoming catering auctions |

## Setup

### Prerequisites
- Python 3.10+
- Chromium (installed via Playwright)

### Installation

```bash
# Clone and enter
git clone https://github.com/Marios-vvs/Coffee-project.git
cd Coffee-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Install headless Chromium (required for scraping)
playwright install chromium
```

### Windows Note
If PowerShell blocks the venv activation, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Usage

```bash
# Run once — scrape all sites, export to Excel
python main.py

# Quick test with mock data (no scraping)
python main.py --test

# Scheduled mode — runs at 09:00 and 21:00 daily
python main.py --schedule
```

Output: `coffee_deals_YYYYMMDD_HHMMSS.xlsx` in the current directory.

## Project Structure

```
Coffee-project/
├── main.py                 # Entry point — orchestrates the pipeline
├── scrapers.py             # Playwright-powered auction site scrapers
├── reference_prices.py     # Price database (80+ machines) + matching engine
├── excel_export.py         # Formatted Excel workbook export
├── requirements.txt        # Python dependencies
└── README.md
```

## Architecture Notes

**Why Playwright instead of requests?**
UK auction sites (John Pye, i-bidder, Bidspotter, etc.) use Cloudflare and JS-based bot detection. Raw HTTP requests get 403 Forbidden. Playwright runs a real headless Chromium browser that renders JavaScript, passes bot checks, and loads dynamic content. If Playwright isn't installed, the scrapers fall back to raw requests but most sites will block them.

**Tuning CSS selectors:**
The CSS selectors in each scraper are best-effort based on common patterns. Auction sites change their HTML frequently. If a scraper stops finding results:
1. Open the site in Chrome
2. Right-click a listing → Inspect
3. Update the selectors in the relevant scraper class

**Adding new machines:**
Edit `reference_prices.py` → `REFERENCE_MACHINES` dict. Format:
```python
"search key lowercase": {
    "brand": "Display Name",
    "model": "Model Name",
    "retail_gbp": 1234,
    "category": "prosumer"  # or "commercial_single" / "commercial_multi"
}
```

## Rating System

| Rating | Discount | Meaning |
|--------|----------|---------|
| 🔥 STRONG BUY | 60%+ | Exceptional deal — act fast |
| ✅ GOOD DEAL | 40–60% | Worth bidding |
| ⚠️ FAIR | 20–40% | Marginal opportunity |
| ❌ OVERPRICED | <20% | Skip |

Conservative resale assumes 65% of retail price for refurbished equipment.
