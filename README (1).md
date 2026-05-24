# 💰 Automated Price Tracker & Web Scraper

A smart async Python script that **scrapes product pages across e-commerce sites**, tracks price history, and **alerts you instantly** via Telegram, Discord, or Email the moment a price drops to your target.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![aiohttp](https://img.shields.io/badge/async-aiohttp-green?style=flat-square)
![BeautifulSoup](https://img.shields.io/badge/scraper-BeautifulSoup4-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Multi-site scraping** | Amazon, Flipkart, generic shops — or any site |
| **Smart selector fallback** | Auto-detects price using 12+ common selectors |
| **Custom selectors** | Per-product CSS selectors for precision |
| **Price history** | Stores 90 data points per product in JSON |
| **3 alert channels** | Telegram, Discord Webhook, Email (SMTP) |
| **Anti-bot measures** | Rotating user-agents, request delays, async |
| **Live dashboard** | Open `dashboard/index.html` — sparklines, alerts, history table |
| **Zero spam** | Only alerts when price drops ≤ your target |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/price-tracker.git
cd price-tracker
pip install -r requirements.txt
```

### 2. Add your products

Edit `config/config.yaml`:

```yaml
interval_minutes: 30

products:
  - name: "Sony WH-1000XM5"
    url: "https://www.amazon.in/dp/B09XS7JWHH"
    target_price: 22000
    currency: "₹"

telegram:
  enabled: true
  token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
```

### 3. Run

```bash
python tracker.py
```

---

## 🧪 Test Without Real Shopping Sites

Use `books.toscrape.com` — a safe, legal scraping sandbox:

```yaml
- name: "Test Book"
  url: "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
  target_price: 60.00
  currency: "£"
  price_selectors:
    - "p.price_color"
```

---

## 🎯 Adding Site-Specific Selectors

For best accuracy, right-click a price on any site → **Inspect** → copy the CSS selector:

```yaml
# Amazon India
price_selectors:
  - "span.a-price-whole"
  - "#priceblock_ourprice"

# Flipkart
price_selectors:
  - "._30jeq3._16Jk6d"

# Any generic site
price_selectors:
  - ".price"
  - "[data-price]"
  - "[itemprop='price']"
```

---

## 📬 Alert Setup

### Telegram (Recommended)
1. Message [@BotFather](https://t.me/botfather) → `/newbot` → copy token
2. Message [@userinfobot](https://t.me/userinfobot) → copy your `chat_id`
3. Set both in `config/config.yaml`

### Discord
1. Server → Integrations → Webhooks → New Webhook
2. Copy URL into config

### Email (Gmail)
1. Enable 2FA → generate [App Password](https://myaccount.google.com/apppasswords)
2. Use App Password (not your Gmail password) in config

---

## 🖥️ Dashboard

Open `dashboard/index.html` in a browser for:
- Live price cards with sparklines
- Target hit indicators
- Alert log
- Price history table

---

## 📁 Project Structure

```
price-tracker/
├── tracker.py              # Main scraper + orchestrator
├── requirements.txt
├── config/
│   └── config.yaml         # Products + alert credentials
├── alerts/
│   └── notifier.py         # Email / Telegram / Discord alerters
├── dashboard/
│   └── index.html          # Live browser dashboard
└── data/
    ├── tracker.log         # Human-readable log
    ├── price_history.json  # Price records (auto-created)
    └── alerts_log.json     # Alert history (auto-created)
```

---

## ⚙️ Run as Background Service (Linux)

```ini
# /etc/systemd/system/price-tracker.service
[Unit]
Description=Price Tracker
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/tracker.py
WorkingDirectory=/path/to/price-tracker
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable price-tracker && sudo systemctl start price-tracker
```

---

## ⚠️ Ethical Scraping

- Respect `robots.txt` — check before scraping a site
- Use intervals ≥ 30 minutes to avoid overloading servers
- Some sites (Amazon, Flipkart) actively block scrapers — use official APIs when available

---

## 📄 License

MIT
