import os
import requests
from typing import List, Dict


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def notify_telegram(jobs: List[Dict], max_jobs: int = 15):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram secrets not set")

    if not jobs:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    lines = []
    lines.append(f"🆕 New Jobs Added ({len(jobs)})\n")

    current_company = None

    for job in jobs[:max_jobs]:
        company = job.get("company")
        title = job.get("title", "N/A")
        link = job.get("posting_url", "")
        locations = job.get("locations") or []
        location_text = ", ".join(locations) if locations else "Location not specified"

        if company != current_company:
            lines.append(f"\n📌 {company}")
            current_company = company

        lines.append(f"{title}")
        lines.append(f"{location_text}")
        lines.append(f"{link}\n")

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "\n".join(lines),
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
