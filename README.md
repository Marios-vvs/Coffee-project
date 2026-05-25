# ☕ Coffee Machine Arbitrage Tracker

A Python tool that scrapes UK auction houses for underpriced premium coffee equipment, matches listings against a reference price database, calculates arbitrage potential, and exports results to a formatted Excel workbook.

## Strategy

UK auction houses that handle café closures, restaurant liquidations, and retail returns often sell premium espresso machines at 40-80% below retail. These sites have far less competition than eBay or Facebook Marketplace because:
- Buyers need to register with the auction house
- Collection is often required (no shipping)
- Listings are buried in mixed-category sales
- The coffee-specific buyer community doesn't monitor these as closely

This tool automates the monitoring so you can bid on the best deals before they close.

## Target Sites

| Site | Type | Why It's Good |
|------|------|---------------|
| **John Pye** | UK's largest commercial auctioneer | Retail returns from major retailers, ex-display stock |
| **i-bidder** | Auction aggregator (100s of houses) | Aggregates Ramco, EAMA, and many smaller auctioneers |
| **Bidspotter** | Industrial/commercial aggregator | Pro Auction, Robson Kay — specialist café clearances |
| **BPI Auctions** | Business liquidation specialist | Catering equipment from insolvency/closures |
| **Pro Auction** | Restaurant/café clearance specialist | Often handles complete London café closures |
| **Wilsons Auctions** | Largest independent UK/Ireland | Government surplus, police seizures, insolvency |
| **Auction News** | Meta-aggregator | Lists upcoming catering sales across all houses |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│  Orchestrator: scrape → match → enrich → export     │
└─────────┬───────────────────────────────┬───────────┘
          │                               │
          ▼                               ▼
┌──────────────────┐          ┌──────────────────────┐
│   scrapers.py    │          │  reference_prices.py  │
│                  │          │                        │
│ • JohnPyeScraper │          │ • 80+ premium machines │
│ • IBidderScraper │──match──▶│ • Brand/model/retail £ │
│ • BidspotterScrp │          │ • Arbitrage calculator  │
│ • BPIAuctions    │          │ • Keyword matching      │
│ • ProAuction     │          └──────────────────────┘
│ • WilsonsAuction │                    │
│ • AuctionNews    │                    ▼
└──────────────────┘          ┌──────────────────────┐
                              │   excel_export.py     │
                              │                        │
                              │ • Deals Dashboard      │
                              │ • Reference Prices     │
                              │ • Scrape Log           │
                              └──────────────────────┘
```

## Usage

```bash
# One-off run: scrape all sites, export Excel
python main.py

# Scheduled mode: runs at 09:00 and 21:00 daily
python main.py --schedule

# Test with mock data (verify Excel formatting)
python main.py --test
```

## Output

The Excel workbook contains three sheets:

1. **☕ Deals Dashboard** — All matched listings sorted by opportunity
   - Rating: 🔥 STRONG BUY (60%+) / ✅ GOOD DEAL (40-60%) / ⚠️ FAIR / ❌ OVERPRICED
   - Current bid vs retail price
   - Conservative profit estimate (assumes 65% of retail resale)
   - Direct links to auction lots

2. **📊 Reference Prices** — Full database of 80+ premium machines with retail prices

3. **📋 Scrape Log** — Metadata, stats, and source breakdown

## Adding New Machines

Edit `reference_prices.py` and add entries to `REFERENCE_MACHINES`:

```python
"brand model keywords": {
    "brand": "Brand Name",
    "model": "Model Name",
    "retail_gbp": 1500,
    "category": "prosumer"  # or "commercial_single" or "commercial_multi"
}
```

## Adding New Auction Sites

Create a new class in `scrapers.py` that extends `BaseScraper`:

```python
class MyNewScraper(BaseScraper):
    name = "My Auction Site"
    base_url = "https://..."

    def scrape(self) -> list[AuctionListing]:
        # Fetch, parse, return listings
        ...
```

Then add it to `ALL_SCRAPERS` at the bottom of the file.

## Important Notes

- **Scraping is fragile.** Auction sites change their HTML structure. When a scraper breaks, check the CSS selectors in that scraper class.
- **Be polite.** The scrapers include 1-1.5 second delays between requests. Don't reduce these.
- **Collection logistics matter.** Factor in travel/shipping costs when evaluating deals. A £200 saving isn't worth a 400-mile round trip.
- **VAT/Buyer's Premium.** Most auction houses charge 15-25% buyer's premium on top of the hammer price. Factor this into your calculations.
- **Test before you rely on it.** Run with `--test` first to verify the Excel output looks right.

## Dependencies

```
pip install requests beautifulsoup4 openpyxl schedule
```
