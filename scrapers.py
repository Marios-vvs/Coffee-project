"""
Coffee Machine Auction Scraper
Scrapes UK auction houses for premium coffee equipment deals.
Targets low-competition liquidation/auction sites, NOT eBay/Amazon.

Uses Playwright (headless Chromium) to bypass bot detection.
Falls back to raw requests if Playwright is unavailable.
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

# Try to import Playwright; flag availability
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scraper")

# Common headers for the requests fallback
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
    """
    Base class for auction site scrapers.

    Uses Playwright (headless Chromium) as primary fetch method to bypass
    anti-bot protections (Cloudflare, JS challenges, etc.). Falls back to
    raw requests if Playwright is not installed.
    """
    name = "base"
    base_url = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._playwright = None
        self._browser = None

    def _get_browser(self):
        """Lazily launch Playwright browser (reused across fetches)."""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
        return self._browser

    def close(self):
        """Clean up browser resources. Call when done scraping."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def fetch(self, url: str, params: dict = None, wait_selector: str = None) -> Optional[BeautifulSoup]:
        """
        Fetch a page and return parsed BeautifulSoup.

        Primary: Playwright headless browser (bypasses JS/Cloudflare).
        Fallback: raw requests (works for simpler sites).
        """
        # Build full URL with params
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"

        # Try Playwright first
        browser = self._get_browser()
        if browser:
            try:
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    viewport={"width": 1920, "height": 1080},
                    locale="en-GB",
                )
                page = context.new_page()

                # Block images/fonts/media to speed up loading
                page.route("**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf,mp4,mp3}", lambda route: route.abort())

                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for a specific selector if provided, otherwise wait for network idle
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=10000)
                    except PlaywrightTimeout:
                        logger.debug(f"[{self.name}] Selector '{wait_selector}' not found, continuing with page as-is")
                else:
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except PlaywrightTimeout:
                        pass  # Page loaded enough, continue

                html = page.content()
                context.close()
                return BeautifulSoup(html, "html.parser")

            except Exception as e:
                logger.warning(f"[{self.name}] Playwright fetch failed for {url}: {e}")
                try:
                    context.close()
                except Exception:
                    pass

        # Fallback to requests
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.error(f"[{self.name}] Requests fallback also failed for {url}: {e}")
            return None

    def fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """Fetch JSON endpoint (uses requests — no browser needed)."""
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
        cleaned = re.sub(r'[£$€,]', '', text)
        cleaned = re.sub(r'(gbp|eur|usd|vat|inc|ex|starting|current|bid)', '', cleaned, flags=re.IGNORECASE)
        match = re.search(r'(\d+(?:\.\d{1,2})?)', cleaned.strip())
        if match:
            return float(match.group(1))
        return None


class JohnPyeScraper(BaseScraper):
    """
    John Pye Auctions - UK's largest commercial auction house.
    Timed online auctions: retail returns, ex-display, liquidation stock.
    """
    name = "John Pye"
    base_url = "https://www.johnpyeauctions.co.uk"

    SEARCH_TERMS = [
        "coffee machine", "espresso machine", "sage barista", "delonghi specialista",
        "la marzocco", "jura", "sage oracle", "coffee grinder",
        "delonghi magnifica", "delonghi eletta", "nespresso",
    ]

    def scrape(self) -> list[AuctionListing]:
        listings = []
        for term in self.SEARCH_TERMS:
            logger.info(f"[{self.name}] Searching: {term}")
            soup = self.fetch(
                f"{self.base_url}/Search",
                params={"q": term},
                wait_selector=".lot-card, .search-result-item, [class*='lot']",
            )
            if not soup:
                continue

            lot_cards = soup.select(".lot-card, .search-result-item, .lot-item, [class*='lot'], [class*='auction-item']")
            if not lot_cards:
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

            time.sleep(1)

        self.close()
        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class IBidderScraper(BaseScraper):
    """
    i-bidder.com (also powers the-saleroom.com)
    Major UK auction aggregator — searches across hundreds of auction houses.
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
            soup = self.fetch(
                f"{self.base_url}/en-gb/search",
                params={"query": term},
                wait_selector=".lot-tile, .search-lot, [class*='lot-card']",
            )
            if not soup:
                continue

            lot_cards = soup.select(".lot-tile, .search-lot, [class*='lot-card'], .lot-result, .lot")
            if not lot_cards:
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

        self.close()
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
            soup = self.fetch(
                f"{self.base_url}/en-gb/search",
                params={"q": term},
                wait_selector=".lot-card, .lot-tile, [class*='lot-item']",
            )
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

        self.close()
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
            soup = self.fetch(
                f"{self.base_url}/search",
                params={"q": term},
                wait_selector=".lot, .auction-lot, [class*='lot']",
            )
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

        self.close()
        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class ProAuctionScraper(BaseScraper):
    """
    Pro Auction Limited - specialist in restaurant/café clearances.
    Often handle complete café closures in London and SE England.
    """
    name = "Pro Auction"
    base_url = "https://www.proauction.ltd.uk"

    def scrape(self) -> list[AuctionListing]:
        listings = []
        logger.info(f"[{self.name}] Checking current auctions...")

        for path in ["/current-sales", "/auctions", "/sales", "/"]:
            soup = self.fetch(f"{self.base_url}{path}")
            if not soup:
                continue

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

        self.close()
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
            soup = self.fetch(
                f"{self.base_url}/search",
                params={"q": term},
                wait_selector=".lot, [class*='lot'], .auction-item",
            )
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

        self.close()
        logger.info(f"[{self.name}] Found {len(listings)} listings")
        return listings


class AuctionNewsScraper(BaseScraper):
    """
    AuctionNews.com - aggregator that lists upcoming catering equipment auctions.
    Good meta-source to find sales we might miss.
    """
    name = "Auction News"
    base_url = "https://auctionnews.com"

    def scrape(self) -> list[AuctionListing]:
        listings = []
        logger.info(f"[{self.name}] Checking catering equipment auctions...")

        soup = self.fetch(f"{self.base_url}/categories/food-industry-auctions/catering-equipment-auctions")
        if not soup:
            self.close()
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

        self.close()
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
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning(
            "Playwright not installed — falling back to raw requests. "
            "Most auction sites will block this. Install with: "
            "pip install playwright && playwright install chromium"
        )

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
    print(f"Playwright available: {PLAYWRIGHT_AVAILABLE}")
    listings = run_all_scrapers()
    print(f"\nTotal listings found: {len(listings)}")
    for l in listings[:10]:
        print(f"  [{l.source}] {l.title[:80]} - £{l.current_bid}")
