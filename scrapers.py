"""
Coffee Machine Auction Scraper
Scrapes UK auction houses for premium coffee equipment deals.
Targets low-competition liquidation/auction sites, NOT eBay/Amazon.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scraper")

# Common headers to avoid bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

@dataclass
class AuctionListing:
    """Represents a single auction listing."""
    source: str                    # Which auction site
    title: str                     # Lot title/description
    current_bid: Optional[float]   # Current bid in GBP (None if not yet bid)
    url: str                       # Direct link to the lot
    lot_number: Optional[str] = None
    end_time: Optional[str] = None # When the auction ends
    location: Optional[str] = None # Collection location
    condition: Optional[str] = None
    image_url: Optional[str] = None
    retail_price_listed: Optional[float] = None  # RRP if shown on the site
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return asdict(self)


class BaseScraper:
    """Base class for auction site scrapers."""
    name = "base"
    base_url = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed soup."""
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.error(f"[{self.name}] Failed to fetch {url}: {e}")
            return None

    def fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """Fetch JSON endpoint."""
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.error(f"[{self.name}] Failed to fetch JSON {url}: {e}")
            return None

    def scrape(self) -> list[AuctionListing]:
        """Override in subclasses. Returns list of AuctionListing."""
        raise NotImplementedError

    def _parse_price(self, text: str) -> Optional[float]:
        """Extract a numeric price from text like '£150.00' or 'GBP 150'."""
        if not text:
            return None
        # Remove currency symbols and common text
        cleaned = re.sub(r'[£$€,]', '', text)
        cleaned = re.sub(r'(gbp|eur|usd|vat|inc|ex|starting|current|bid)', '', cleaned, flags=re.IGNORECASE)
        match = re.search(r'(\d+(?:\.\d{1,2})?)', cleaned.strip())
        if match:
            return float(match.group(1))
        return None


class JohnPyeScraper(BaseScraper):
    """
    John Pye Auctions - UK's largest commercial auction house.
    They run timed online auctions with retail returns, ex-display,
    liquidation stock. Coffee machines appear in appliance/kitchen sales.
    
    Strategy: Search their API/site for coffee machine keywords.
    """
    name = "John Pye"
    base_url = "https://www.johnpyeauctions.co.uk"

    # Search keywords that catch premium machines
    SEARCH_TERMS = [
        "coffee machine", "espresso machine", "sage barista", "delonghi specialista",
        "la marzocco", "jura", "sage oracle", "coffee grinder",
        "delonghi magnifica", "delonghi eletta", "nespresso",
    ]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(f"{self.base_url}/Search", params={"q": term})
            if not soup:
                continue

            # John Pye uses a card-based layout for search results
            lot_cards = soup.select(".lot-card, .search-result-item, .lot-item, [class*='lot'], [class*='auction-item']")
            if not lot_cards:
                # Fallback: look for any links containing lot details
                lot_cards = soup.select("a[href*='LotDetails'], a[href*='lotdetails']")

            for card in lot_cards:
                try:
                    title_el = card.select_one(".lot-title, .title, h3, h4, .lot-name")
                    title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                    link_el = card.select_one("a[href*='LotDetails']") or card if card.name == "a" else None
                    url = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url = href if href.startswith("http") else f"{self.base_url}{href}"

                    price_el = card.select_one(".current-bid, .price, .bid-amount, [class*='price']")
                    price = self._parse_price(price_el.get_text()) if price_el else None

                    lot_num_el = card.select_one(".lot-number, [class*='lot-num']")
                    lot_num = lot_num_el.get_text(strip=True) if lot_num_el else None

                    if title and len(title) > 5:
                        listings.append(AuctionListing(
                            source=self.name,
                            title=title,
                            current_bid=price,
                            url=url,
                            lot_number=lot_num,
                        ))
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing card: {e}")
                    continue

            time.sleep(1)  # Be polite

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class IBidderScraper(BaseScraper):
    """
    i-bidder.com (also powers the-saleroom.com)
    Major UK auction aggregator. Hosts auctions for hundreds of UK auction houses
    including Ramco, Pro Auction, EAMA, etc.
    
    Their search endpoint lets us query across ALL participating auction houses at once.
    """
    name = "i-bidder"
    base_url = "https://www.i-bidder.com"

    SEARCH_TERMS = [
        "espresso machine", "coffee machine la marzocco", "sage barista",
        "delonghi specialista", "rocket espresso", "jura coffee",
        "commercial espresso", "coffee grinder mazzer", "victoria arduino",
    ]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(f"{self.base_url}/en-gb/search", params={"query": term})
            if not soup:
                continue

            # i-bidder uses lot-card or similar elements
            lot_cards = soup.select(".lot-tile, .search-lot, [class*='lot-card'], .lot-result, .lot")
            if not lot_cards:
                # Try broader selectors
                lot_cards = soup.select("a[href*='/lot/'], a[href*='auction-catalogues']")

            for card in lot_cards:
                try:
                    title_el = card.select_one(".lot-title, .title, h3, h4, .lot-description, .lot-name")
                    title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                    link_el = card.select_one("a[href*='/lot/']") or (card if card.name == "a" else None)
                    url = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url = href if href.startswith("http") else f"{self.base_url}{href}"

                    price_el = card.select_one(".current-bid, .price, .hammer-price, [class*='price'], [class*='bid']")
                    price = self._parse_price(price_el.get_text()) if price_el else None

                    # i-bidder often shows RRP
                    rrp_el = card.select_one(".rrp, .retail-price, [class*='rrp']")
                    rrp = self._parse_price(rrp_el.get_text()) if rrp_el else None

                    lot_num_el = card.select_one(".lot-number, [class*='lot-num']")
                    lot_num = lot_num_el.get_text(strip=True) if lot_num_el else None

                    end_el = card.select_one(".end-date, .closing, [class*='end'], [class*='closing']")
                    end_time = end_el.get_text(strip=True) if end_el else None

                    img_el = card.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    if title and len(title) > 5:
                        listings.append(AuctionListing(
                            source=self.name,
                            title=title,
                            current_bid=price,
                            url=url,
                            lot_number=lot_num,
                            end_time=end_time,
                            image_url=img_url,
                            retail_price_listed=rrp,
                        ))
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing card: {e}")
                    continue

            time.sleep(1.5)

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class BidspotterScraper(BaseScraper):
    """
    Bidspotter.co.uk - UK industrial and commercial auction platform.
    Hosts Pro Auction, Robson Kay, and other specialist auctioneers.
    Good for café closure / restaurant liquidation lots.
    """
    name = "Bidspotter"
    base_url = "https://www.bidspotter.co.uk"

    SEARCH_TERMS = [
        "espresso", "coffee machine", "la marzocco", "grinder commercial coffee",
        "sage oracle", "barista", "cappuccino machine",
    ]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(f"{self.base_url}/en-gb/search", params={"q": term})
            if not soup:
                continue

            lot_cards = soup.select(".lot-card, .lot-tile, [class*='lot-item'], .search-result")
            if not lot_cards:
                lot_cards = soup.select("a[href*='catalogue']")

            for card in lot_cards:
                try:
                    title_el = card.select_one(".lot-title, .title, h3, h4")
                    title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                    link_el = card.select_one("a") or (card if card.name == "a" else None)
                    url = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url = href if href.startswith("http") else f"{self.base_url}{href}"

                    price_el = card.select_one("[class*='price'], [class*='bid']")
                    price = self._parse_price(price_el.get_text()) if price_el else None

                    if title and len(title) > 5:
                        listings.append(AuctionListing(
                            source=self.name,
                            title=title,
                            current_bid=price,
                            url=url,
                        ))
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing card: {e}")
                    continue

            time.sleep(1)

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class BPIAuctionsScraper(BaseScraper):
    """
    BPI Auctions - specialist in business/catering/industrial liquidation.
    Particularly good for catering equipment from café closures.
    """
    name = "BPI Auctions"
    base_url = "https://www.bpiauctions.com"

    SEARCH_TERMS = [
        "coffee", "espresso", "grinder", "barista",
    ]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(f"{self.base_url}/search", params={"q": term})
            if not soup:
                continue

            lot_cards = soup.select(".lot, .auction-lot, [class*='lot'], .search-result, .item")

            for card in lot_cards:
                try:
                    title_el = card.select_one(".title, h3, h4, .lot-title, .lot-name")
                    title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                    link_el = card.select_one("a")
                    url = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url = href if href.startswith("http") else f"{self.base_url}{href}"

                    price_el = card.select_one("[class*='price'], [class*='bid']")
                    price = self._parse_price(price_el.get_text()) if price_el else None

                    location_el = card.select_one("[class*='location'], .venue")
                    location = location_el.get_text(strip=True) if location_el else None

                    if title and len(title) > 5:
                        listings.append(AuctionListing(
                            source=self.name,
                            title=title,
                            current_bid=price,
                            url=url,
                            location=location,
                        ))
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing card: {e}")
                    continue

            time.sleep(1)

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class ProAuctionScraper(BaseScraper):
    """
    Pro Auction Limited - specialist in restaurant/café clearances.
    Often handle complete café closures in London and SE England.
    Listed on Bidspotter but also have their own catalogue pages.
    """
    name = "Pro Auction"
    base_url = "https://www.proauction.ltd.uk"

    def scrape(self) -> list[AuctionListing]:
        listings = []
        logger.info(f"[{self.name}] Checking current auctions...")

        # Pro Auction often lists current sales on their homepage / sales page
        for path in ["/current-sales", "/auctions", "/sales", "/"]:
            soup = self.fetch(f"{self.base_url}{path}")
            if not soup:
                continue

            # Look for any links to auction catalogues or lot pages
            auction_links = soup.select("a[href*='auction'], a[href*='sale'], a[href*='lot'], a[href*='catalogue']")
            for link in auction_links:
                text = link.get_text(strip=True).lower()
                if any(kw in text for kw in ["coffee", "catering", "restaurant", "cafe", "café", "kitchen", "espresso"]):
                    href = link.get("href", "")
                    url = href if href.startswith("http") else f"{self.base_url}{href}"
                    listings.append(AuctionListing(
                        source=self.name,
                        title=link.get_text(strip=True),
                        current_bid=None,
                        url=url,
                    ))
            time.sleep(1)

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class WilsonsAuctionsScraper(BaseScraper):
    """
    Wilsons Auctions - largest independent auction company in UK & Ireland.
    Handle government surplus, insolvency, police seizures.
    """
    name = "Wilsons Auctions"
    base_url = "https://www.wilsonsauctions.com"

    SEARCH_TERMS = ["coffee machine", "espresso", "catering equipment"]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(f"{self.base_url}/search", params={"q": term})
            if not soup:
                continue

            lot_cards = soup.select(".lot, [class*='lot'], .auction-item, .search-result")
            for card in lot_cards:
                try:
                    title_el = card.select_one(".title, h3, h4, .lot-title")
                    title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                    link_el = card.select_one("a")
                    url = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url = href if href.startswith("http") else f"{self.base_url}{href}"

                    price_el = card.select_one("[class*='price'], [class*='bid']")
                    price = self._parse_price(price_el.get_text()) if price_el else None

                    if title and len(title) > 5:
                        listings.append(AuctionListing(
                            source=self.name,
                            title=title,
                            current_bid=price,
                            url=url,
                        ))
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing card: {e}")
                    continue

            time.sleep(1)

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class AuctionNewsScraper(BaseScraper):
    """
    AuctionNews.com - aggregator that lists upcoming catering equipment auctions
    from multiple UK auction houses. Good meta-source to find sales we might miss.
    """
    name = "Auction News"
    base_url = "https://auctionnews.com"

    def scrape(self) -> list[AuctionListing]:
        listings = []
        logger.info(f"[{self.name}] Checking catering equipment auctions...")

        soup = self.fetch(f"{self.base_url}/categories/food-industry-auctions/catering-equipment-auctions")
        if not soup:
            return listings

        auction_cards = soup.select(".auction-card, .listing, article, [class*='auction']")
        for card in auction_cards:
            try:
                title_el = card.select_one("h2, h3, h4, .title")
                title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:200]

                link_el = card.select_one("a")
                url = ""
                if link_el and link_el.get("href"):
                    href = link_el["href"]
                    url = href if href.startswith("http") else f"{self.base_url}{href}"

                if title and len(title) > 5:
                    listings.append(AuctionListing(
                        source=self.name,
                        title=title,
                        current_bid=None,
                        url=url,
                        condition="Auction listing - check for coffee equipment",
                    ))
            except Exception as e:
                logger.debug(f"[{self.name}] Error parsing card: {e}")
                continue

        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


# Registry of all scrapers
ALL_SCRAPERS = [
    JohnPyeScraper,
    IBidderScraper,
    BidspotterScraper,
    BPIAuctionsScraper,
    ProAuctionScraper,
    WilsonsAuctionsScraper,
    AuctionNewsScraper,
]


def run_all_scrapers() -> list[AuctionListing]:
    """Run all scrapers and return combined results."""
    all_listings = []
    for scraper_cls in ALL_SCRAPERS:
        try:
            scraper = scraper_cls()
            results = scraper.scrape()
            all_listings.extend(results)
        except Exception as e:
            logger.error(f"Scraper {scraper_cls.name} failed entirely: {e}")
    return all_listings


if __name__ == "__main__":
    print("Running all scrapers...")
    listings = run_all_scrapers()
    print(f"\nTotal listings found: {len(listings)}")
    for l in listings[:10]:
        print(f"  [{l.source}] {l.title[:80]} - £{l.current_bid}")
