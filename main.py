"""
Coffee Arbitrage Tracker - Main Orchestrator
Runs scrapers, matches against reference prices, calculates arbitrage potential,
and exports results to a formatted Excel workbook.

Usage:
    python main.py              # Run once, export to Excel
    python main.py --schedule   # Run on 12-hour schedule (9am/9pm)
    python main.py --test       # Quick test with mock data
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import run_all_scrapers, AuctionListing
from reference_prices import match_listing_to_reference, calculate_arbitrage, REFERENCE_MACHINES
from excel_export import export_to_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log"),
    ]
)
logger = logging.getLogger("main")


def deduplicate_listings(listings: list[AuctionListing]) -> list[AuctionListing]:
    """Remove duplicate listings based on URL or title+source combo."""
    seen = set()
    unique = []
    for listing in listings:
        # Primary dedup key: URL (if present)
        if listing.url:
            key = listing.url
        else:
            key = f"{listing.source}:{listing.title[:100]}"

        if key not in seen:
            seen.add(key)
            unique.append(listing)
    return unique


def filter_premium_only(listings: list[AuctionListing]) -> list[dict]:
    """
    Match listings against reference prices and filter to only premium machines.
    Returns enriched dicts with arbitrage calculations.
    """
    enriched = []
    unmatched_interesting = []

    for listing in listings:
        ref = match_listing_to_reference(listing.title)

        if ref:
            entry = listing.to_dict()
            entry["matched_brand"] = ref["brand"]
            entry["matched_model"] = ref["model"]
            entry["retail_price_ref"] = ref["retail_gbp"]
            entry["category"] = ref["category"]

            # Calculate arbitrage if we have a current bid
            if listing.current_bid is not None and listing.current_bid > 0:
                arb = calculate_arbitrage(listing.current_bid, ref)
                entry.update(arb)
            else:
                entry["discount_pct"] = None
                entry["gross_potential"] = None
                entry["conservative_profit"] = None
                entry["conservative_resale"] = None
                entry["rating"] = "🔍 CHECK BID"

            enriched.append(entry)
        else:
            # Check if title contains any premium brand keywords at all
            title_lower = listing.title.lower()
            premium_keywords = [
                "la marzocco", "marzocco", "sage", "breville", "rocket",
                "ecm", "lelit", "victoria arduino", "nuova simonelli",
                "sanremo", "mazzer", "mahlkonig", "eureka", "jura",
                "delonghi specialista", "de'longhi specialista",
                "dalla corte", "slayer", "decent", "profitec", "niche",
                "ceado", "oracle", "dual boiler",
            ]
            if any(kw in title_lower for kw in premium_keywords):
                entry = listing.to_dict()
                entry["matched_brand"] = "⚠️ MANUAL CHECK"
                entry["matched_model"] = "Unknown model"
                entry["retail_price_ref"] = None
                entry["category"] = "unknown"
                entry["discount_pct"] = None
                entry["gross_potential"] = None
                entry["conservative_profit"] = None
                entry["conservative_resale"] = None
                entry["rating"] = "🔍 MANUAL CHECK"
                enriched.append(entry)

    return enriched


def sort_by_opportunity(listings: list[dict]) -> list[dict]:
    """Sort listings by best arbitrage opportunity first."""
    def sort_key(item):
        # Priority 1: Has a discount percentage (higher is better)
        discount = item.get("discount_pct")
        if discount is not None:
            return (-discount,)  # Negative for descending
        # Priority 2: No discount info but matched a brand
        if item.get("matched_brand") != "⚠️ MANUAL CHECK":
            return (0,)
        # Priority 3: Manual check items last
        return (100,)

    return sorted(listings, key=sort_key)


def save_raw_json(listings: list[dict], output_dir: str = "."):
    """Save raw results as JSON for debugging/archival."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"raw_results_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(listings, f, indent=2, default=str)
    logger.info(f"Raw results saved to {path}")
    return path


def run_pipeline(output_dir: str = "/mnt/user-data/outputs") -> str:
    """
    Full pipeline: scrape → match → enrich → sort → export.
    Returns path to the Excel file.
    """
    logger.info("=" * 60)
    logger.info("COFFEE ARBITRAGE TRACKER - Starting pipeline")
    logger.info("=" * 60)

    # Step 1: Scrape all sources
    logger.info("Step 1: Running scrapers...")
    raw_listings = run_all_scrapers()
    logger.info(f"  Raw listings collected: {len(raw_listings)}")

    # Step 2: Deduplicate
    logger.info("Step 2: Deduplicating...")
    unique_listings = deduplicate_listings(raw_listings)
    logger.info(f"  Unique listings: {len(unique_listings)}")

    # Step 3: Match against reference prices & filter
    logger.info("Step 3: Matching against reference database...")
    enriched = filter_premium_only(unique_listings)
    logger.info(f"  Premium matches: {len(enriched)}")

    # Step 4: Sort by opportunity
    logger.info("Step 4: Sorting by opportunity...")
    sorted_listings = sort_by_opportunity(enriched)

    # Step 5: Export
    logger.info("Step 5: Exporting to Excel...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_path = os.path.join(output_dir, f"coffee_deals_{timestamp}.xlsx")
    export_to_excel(sorted_listings, excel_path)
    logger.info(f"  Excel exported to: {excel_path}")

    # Also save raw JSON
    save_raw_json(sorted_listings, os.path.dirname(excel_path) if os.path.dirname(excel_path) else ".")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    strong_buys = [l for l in sorted_listings if l.get("rating") == "🔥 STRONG BUY"]
    good_deals = [l for l in sorted_listings if l.get("rating") == "✅ GOOD DEAL"]
    logger.info(f"  🔥 Strong buys (60%+ off): {len(strong_buys)}")
    logger.info(f"  ✅ Good deals (40-60% off): {len(good_deals)}")
    logger.info(f"  Total premium listings: {len(sorted_listings)}")

    for item in sorted_listings[:5]:
        brand = item.get("matched_brand", "?")
        model = item.get("matched_model", "?")
        bid = item.get("current_bid", "?")
        retail = item.get("retail_price_ref", "?")
        rating = item.get("rating", "?")
        logger.info(f"  {rating} {brand} {model} - Bid: £{bid} / Retail: £{retail} [{item['source']}]")

    return excel_path


def run_with_test_data(output_dir: str = "/mnt/user-data/outputs") -> str:
    """Run pipeline with mock data to verify export formatting."""
    logger.info("Running with TEST DATA...")

    test_listings = [
        {
            "source": "John Pye", "title": "SAGE ORACLE TOUCH COFFEE MACHINE",
            "current_bid": 320.0, "url": "https://johnpyeauctions.co.uk/lot/12345",
            "lot_number": "LOT 45", "end_time": "2026-05-26 20:00",
            "location": "Nottingham", "condition": "Retail return",
            "image_url": None, "retail_price_listed": 1999.99,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Sage", "matched_model": "Oracle Touch",
            "retail_price_ref": 2000, "category": "prosumer",
            "retail_price": 2000, "current_price": 320.0,
            "discount_pct": 84.0, "gross_potential": 1680.0,
            "conservative_resale": 1300.0, "conservative_profit": 980.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "i-bidder", "title": "La Marzocco Linea Mini Espresso Machine - Black",
            "current_bid": 1200.0, "url": "https://i-bidder.com/lot/67890",
            "lot_number": "142", "end_time": "2026-05-27 14:00",
            "location": "London", "condition": "Used - café closure",
            "image_url": None, "retail_price_listed": 3800.0,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "La Marzocco", "matched_model": "Linea Mini",
            "retail_price_ref": 3800, "category": "commercial_single",
            "retail_price": 3800, "current_price": 1200.0,
            "discount_pct": 68.4, "gross_potential": 2600.0,
            "conservative_resale": 2470.0, "conservative_profit": 1270.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "BPI Auctions", "title": "DE'LONGHI SPECIALISTA MAESTRO EC9665.M",
            "current_bid": 180.0, "url": "https://bpiauctions.com/lot/11111",
            "lot_number": "LOT 88", "end_time": "2026-05-28 10:00",
            "location": "Birmingham", "condition": "Retail return, untested",
            "image_url": None, "retail_price_listed": 699.99,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "De'Longhi", "matched_model": "Specialista Maestro",
            "retail_price_ref": 700, "category": "prosumer",
            "retail_price": 700, "current_price": 180.0,
            "discount_pct": 74.3, "gross_potential": 520.0,
            "conservative_resale": 455.0, "conservative_profit": 275.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "Bidspotter", "title": "Mazzer Super Jolly Electronic Coffee Grinder",
            "current_bid": 95.0, "url": "https://bidspotter.co.uk/lot/22222",
            "lot_number": "LOT 12", "end_time": "2026-05-26 16:00",
            "location": "London - Camden", "condition": "Café clearance",
            "image_url": None, "retail_price_listed": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Mazzer", "matched_model": "Super Jolly",
            "retail_price_ref": 800, "category": "prosumer",
            "retail_price": 800, "current_price": 95.0,
            "discount_pct": 88.1, "gross_potential": 705.0,
            "conservative_resale": 520.0, "conservative_profit": 425.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "Wilsons Auctions", "title": "Jura Z10 Bean to Cup Coffee Machine",
            "current_bid": 650.0, "url": "https://wilsonsauctions.com/lot/33333",
            "lot_number": "LOT 201", "end_time": "2026-05-30 12:00",
            "location": "Belfast", "condition": "Police seizure",
            "image_url": None, "retail_price_listed": 2499.99,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Jura", "matched_model": "Z10",
            "retail_price_ref": 2500, "category": "prosumer",
            "retail_price": 2500, "current_price": 650.0,
            "discount_pct": 74.0, "gross_potential": 1850.0,
            "conservative_resale": 1625.0, "conservative_profit": 975.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "i-bidder", "title": "Nuova Simonelli Aurelia II 2 Group Espresso",
            "current_bid": 1800.0, "url": "https://i-bidder.com/lot/44444",
            "lot_number": "305", "end_time": "2026-05-29 11:00",
            "location": "Manchester", "condition": "Restaurant insolvency",
            "image_url": None, "retail_price_listed": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Nuova Simonelli", "matched_model": "Aurelia",
            "retail_price_ref": 8000, "category": "commercial_multi",
            "retail_price": 8000, "current_price": 1800.0,
            "discount_pct": 77.5, "gross_potential": 6200.0,
            "conservative_resale": 5200.0, "conservative_profit": 3400.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "John Pye", "title": "SAGE BARISTA EXPRESS IMPRESS COFFEE MACHINE BES876",
            "current_bid": 250.0, "url": "https://johnpyeauctions.co.uk/lot/55555",
            "lot_number": "LOT 112", "end_time": "2026-05-26 20:00",
            "location": "Marchington", "condition": "Retail return",
            "image_url": None, "retail_price_listed": 549.95,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Sage", "matched_model": "Barista Express",
            "retail_price_ref": 550, "category": "prosumer",
            "retail_price": 550, "current_price": 250.0,
            "discount_pct": 54.5, "gross_potential": 300.0,
            "conservative_resale": 357.5, "conservative_profit": 107.5,
            "rating": "✅ GOOD DEAL",
        },
        {
            "source": "Bidspotter", "title": "Victoria Arduino Eagle One Prima Home Espresso",
            "current_bid": 1500.0, "url": "https://bidspotter.co.uk/lot/66666",
            "lot_number": "LOT 7", "end_time": "2026-05-28 15:00",
            "location": "London - Chalk Farm", "condition": "Café closure",
            "image_url": None, "retail_price_listed": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Victoria Arduino", "matched_model": "Eagle One Prima",
            "retail_price_ref": 3200, "category": "commercial_single",
            "retail_price": 3200, "current_price": 1500.0,
            "discount_pct": 53.1, "gross_potential": 1700.0,
            "conservative_resale": 2080.0, "conservative_profit": 580.0,
            "rating": "✅ GOOD DEAL",
        },
        {
            "source": "BPI Auctions", "title": "Rocket Appartamento Espresso Machine Copper",
            "current_bid": 520.0, "url": "https://bpiauctions.com/lot/77777",
            "lot_number": "LOT 33", "end_time": "2026-05-27 10:00",
            "location": "Leeds", "condition": "Showroom clearance",
            "image_url": None, "retail_price_listed": 1399.00,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Rocket", "matched_model": "Appartamento",
            "retail_price_ref": 1400, "category": "prosumer",
            "retail_price": 1400, "current_price": 520.0,
            "discount_pct": 62.9, "gross_potential": 880.0,
            "conservative_resale": 910.0, "conservative_profit": 390.0,
            "rating": "🔥 STRONG BUY",
        },
        {
            "source": "i-bidder", "title": "Lelit Bianca V3 PL162T Espresso Machine",
            "current_bid": 850.0, "url": "https://i-bidder.com/lot/88888",
            "lot_number": "506", "end_time": "2026-05-29 09:00",
            "location": "Bristol", "condition": "Private sale",
            "image_url": None, "retail_price_listed": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "matched_brand": "Lelit", "matched_model": "Bianca",
            "retail_price_ref": 2000, "category": "prosumer",
            "retail_price": 2000, "current_price": 850.0,
            "discount_pct": 57.5, "gross_potential": 1150.0,
            "conservative_resale": 1300.0, "conservative_profit": 450.0,
            "rating": "✅ GOOD DEAL",
        },
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_path = os.path.join(output_dir, f"coffee_deals_{timestamp}.xlsx")
    export_to_excel(test_listings, excel_path)
    logger.info(f"Test export saved to: {excel_path}")
    return excel_path


if __name__ == "__main__":
    output_dir = "."
    os.makedirs(output_dir, exist_ok=True)

    if "--test" in sys.argv:
        path = run_with_test_data(output_dir)
    elif "--schedule" in sys.argv:
        import schedule
        import time as time_mod
        logger.info("Starting scheduled mode: runs at 09:00 and 21:00 daily")
        schedule.every().day.at("09:00").do(run_pipeline, output_dir=output_dir)
        schedule.every().day.at("21:00").do(run_pipeline, output_dir=output_dir)
        # Also run immediately on start
        run_pipeline(output_dir=output_dir)
        while True:
            schedule.run_pending()
            time_mod.sleep(60)
    else:
        path = run_pipeline(output_dir)
        print(f"\nResults exported to: {path}")
