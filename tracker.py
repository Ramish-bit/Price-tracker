#!/usr/bin/env python3
"""
Automated Price Tracker & Web Scraper
Monitors product prices across e-commerce sites and alerts when targets are hit.
"""

import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path

import aiohttp
import yaml
from bs4 import BeautifulSoup

from alerts.notifier import fire_alerts

# ── Logging ───────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
LOG_FILE  = DATA_DIR / "tracker.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger("price-tracker")

# ── Rotating user agents (avoid bot detection) ────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
]

PRICE_HISTORY_FILE = DATA_DIR / "price_history.json"
ALERTS_FILE        = DATA_DIR / "alerts_log.json"


# ── Config ────────────────────────────────────────────────────────────────────
def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── History helpers ───────────────────────────────────────────────────────────
def load_history() -> dict:
    if PRICE_HISTORY_FILE.exists():
        return json.loads(PRICE_HISTORY_FILE.read_text())
    return {}

def save_history(h: dict):
    PRICE_HISTORY_FILE.write_text(json.dumps(h, indent=2))

def append_alert_log(event: dict):
    log_data = []
    if ALERTS_FILE.exists():
        log_data = json.loads(ALERTS_FILE.read_text())
    log_data.append(event)
    log_data = log_data[-200:]
    ALERTS_FILE.write_text(json.dumps(log_data, indent=2))


# ── Price extraction ──────────────────────────────────────────────────────────
def parse_price(text: str) -> float | None:
    """Extract first numeric price from a string. Handles ₹, $, €, £ etc."""
    text = text.replace(",", "")
    match = re.search(r"[\d]+(?:\.\d{1,2})?", text)
    if match:
        return float(match.group())
    return None

def extract_price(soup: BeautifulSoup, selectors: list[str]) -> float | None:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            price = parse_price(el.get_text(strip=True))
            if price:
                return price
    return None

def extract_title(soup: BeautifulSoup, selectors: list[str]) -> str:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(strip=True)[:120]
    return "Unknown Product"


# ── Scraper ───────────────────────────────────────────────────────────────────
async def scrape_product(session: aiohttp.ClientSession, product: dict) -> dict:
    url      = product["url"]
    name     = product.get("name", "Unnamed Product")
    target   = product.get("target_price")
    currency = product.get("currency", "₹")

    # Selectors: site-specific first, then generic fallbacks
    price_selectors = product.get("price_selectors", []) + [
        # Amazon-style
        "span.a-price-whole", "#priceblock_ourprice", "#priceblock_dealprice",
        "span.a-offscreen", ".a-price .a-offscreen",
        # Generic e-commerce
        "[data-price]", ".price", ".product-price", ".offer-price",
        ".current-price", ".sale-price", "span.price",
        "[itemprop='price']", ".pdp-price",
        # Books / edu sites
        ".buy-price", ".book-price",
    ]
    title_selectors = product.get("title_selectors", []) + [
        "h1#productTitle", "h1.product-title", "h1.pdp-title",
        "h1[itemprop='name']", "h1", ".product-name",
    ]

    headers = {
        "User-Agent"     : random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer"        : "https://www.google.com/",
    }

    try:
        async with session.get(
            url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
            allow_redirects=True, ssl=False
        ) as resp:
            if resp.status != 200:
                return {"name": name, "url": url, "price": None,
                        "error": f"HTTP {resp.status}", "ok": False,
                        "ts": datetime.utcnow().isoformat()}

            html  = await resp.text()
            soup  = BeautifulSoup(html, "html.parser")
            price = extract_price(soup, price_selectors)
            title = extract_title(soup, title_selectors)

            if price is None:
                return {"name": name, "url": url, "price": None, "title": title,
                        "error": "Price not found — add site-specific selector",
                        "ok": False, "ts": datetime.utcnow().isoformat()}

            return {
                "name": name, "url": url, "price": price,
                "currency": currency, "target": target,
                "title": title, "ok": True, "error": None,
                "ts": datetime.utcnow().isoformat(),
                "hit_target": target is not None and price <= target,
            }

    except asyncio.TimeoutError:
        return {"name": name, "url": url, "price": None,
                "error": "Timeout", "ok": False, "ts": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"name": name, "url": url, "price": None,
                "error": str(e), "ok": False, "ts": datetime.utcnow().isoformat()}


# ── Core loop ─────────────────────────────────────────────────────────────────
async def check_all(session: aiohttp.ClientSession, cfg: dict):
    products = cfg["products"]
    history  = load_history()
    delay    = cfg.get("request_delay_seconds", 3)

    results = []
    for product in products:
        result = await scrape_product(session, product)
        results.append(result)

        url   = product["url"]
        name  = result["name"]
        price = result["price"]
        curr  = result.get("currency", "₹")

        if not result["ok"]:
            log.warning("⚠️  %-35s  ERROR: %s", name, result["error"])
        else:
            prev_price = history.get(url, {}).get("latest_price")
            direction  = ""
            if prev_price:
                if price < prev_price:   direction = f"  ↓ was {curr}{prev_price:.2f}"
                elif price > prev_price: direction = f"  ↑ was {curr}{prev_price:.2f}"

            log.info("💰  %-35s  %s%.2f%s", name, curr, price, direction)

            # Update history
            if url not in history:
                history[url] = {"name": name, "prices": []}
            history[url]["latest_price"] = price
            history[url]["prices"].append({"price": price, "ts": result["ts"]})
            history[url]["prices"] = history[url]["prices"][-90:]   # 90 data points

            # Alert if target hit
            if result.get("hit_target"):
                target = result["target"]
                log.info("🎯  TARGET HIT: %s — %s%.2f (target: %s%.2f)",
                         name, curr, price, curr, target)
                await fire_alerts(cfg, result)
                append_alert_log({**result, "event": "target_hit"})

        await asyncio.sleep(delay + random.uniform(0, 1))

    save_history(history)
    return results


async def run():
    cfg      = load_config()
    interval = cfg.get("interval_minutes", 30) * 60
    log.info("🚀 Price Tracker started — %d product(s), checking every %d min",
             len(cfg["products"]), cfg.get("interval_minutes", 30))

    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            log.info("── Checking prices at %s ──", datetime.utcnow().strftime("%H:%M UTC"))
            await check_all(session, cfg)
            log.info("── Done. Next check in %d min ──", cfg.get("interval_minutes", 30))
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(run())
