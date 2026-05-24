"""
Alert dispatcher — Email, Telegram, Discord
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiohttp

log = logging.getLogger("price-tracker.alerts")


async def alert_email(cfg: dict, result: dict):
    ec = cfg.get("email", {})
    if not ec.get("enabled"):
        return

    name     = result["name"]
    price    = result["price"]
    target   = result["target"]
    curr     = result.get("currency", "₹")
    url      = result["url"]

    subject = f"🎯 Price Drop Alert: {name} is now {curr}{price:.2f}!"
    body = (
        f"Great news! A product you're watching has hit your target price.\n\n"
        f"Product  : {name}\n"
        f"Current  : {curr}{price:.2f}\n"
        f"Target   : {curr}{target:.2f}\n"
        f"Savings  : {curr}{target - price:.2f} below your target!\n"
        f"Link     : {url}\n\n"
        f"Checked  : {result['ts']} UTC\n\n"
        f"--- Price Tracker Bot ---"
    )

    try:
        msg = MIMEMultipart()
        msg["From"]    = ec["from"]
        msg["To"]      = ec["to"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL(ec["smtp_host"], ec.get("smtp_port", 465)) as srv:
            srv.login(ec["username"], ec["password"])
            srv.sendmail(ec["from"], ec["to"], msg.as_string())
        log.info("📧 Email alert sent → %s", name)
    except Exception as e:
        log.error("Email alert failed: %s", e)


async def alert_telegram(cfg: dict, result: dict):
    tc = cfg.get("telegram", {})
    if not tc.get("enabled"):
        return

    name   = result["name"]
    price  = result["price"]
    target = result["target"]
    curr   = result.get("currency", "₹")
    saving = target - price

    text = (
        f"🎯 *Price Drop Alert!*\n\n"
        f"📦 *{name}*\n"
        f"💰 Current: *{curr}{price:.2f}*\n"
        f"🎯 Target: `{curr}{target:.2f}`\n"
        f"💚 Below target by: *{curr}{saving:.2f}*\n\n"
        f"🛒 [Buy Now]({result['url']})\n\n"
        f"_Checked: {result['ts']} UTC_"
    )

    url = f"https://api.telegram.org/bot{tc['token']}/sendMessage"
    async with aiohttp.ClientSession() as s:
        try:
            await s.post(url, json={
                "chat_id": tc["chat_id"],
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            })
            log.info("📨 Telegram alert sent → %s", name)
        except Exception as e:
            log.error("Telegram alert failed: %s", e)


async def alert_discord(cfg: dict, result: dict):
    dc = cfg.get("discord", {})
    if not dc.get("enabled"):
        return

    name   = result["name"]
    price  = result["price"]
    target = result["target"]
    curr   = result.get("currency", "₹")
    saving = target - price

    embed = {
        "title"      : f"🎯 Price Drop: {name}",
        "url"        : result["url"],
        "color"      : 0x00C851,
        "description": (
            f"**Current Price:** `{curr}{price:.2f}`\n"
            f"**Your Target:** `{curr}{target:.2f}`\n"
            f"**Below Target by:** `{curr}{saving:.2f}`\n\n"
            f"[🛒 Buy Now]({result['url']})"
        ),
        "footer" : {"text": f"Price Tracker • {result['ts']} UTC"},
        "thumbnail": {"url": "https://i.imgur.com/4M34hi2.png"},
    }

    async with aiohttp.ClientSession() as s:
        try:
            await s.post(dc["webhook_url"], json={"embeds": [embed]})
            log.info("🎮 Discord alert sent → %s", name)
        except Exception as e:
            log.error("Discord alert failed: %s", e)


async def fire_alerts(cfg: dict, result: dict):
    """Send all enabled alerts concurrently."""
    await asyncio.gather(
        alert_email(cfg, result),
        alert_telegram(cfg, result),
        alert_discord(cfg, result),
    )
