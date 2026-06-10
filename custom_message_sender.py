import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("Telegram secrets not set")

def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram bot token or chat ID not set")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
        "parse_mode": "HTML",  # allows basic formatting
    }

    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()

message = """
🚀 <b>JobHunt Dashboard — Major Update</b>

We've shipped a completely redesigned dashboard. Here's what's new:

📅 <b>Day Strip</b>
Pick any day to instantly filter jobs + stats. See exactly how many roles landed on Jun 4 vs Jun 8 — no more guessing.

📊 <b>Live Stats Bar</b>
Stats now update in real time as you filter — by day, location, status, or search. Always reflects what you're actually looking at.

🔍 <b>Smart Search</b>
Search across company, title, job ID, and location simultaneously — results are instant.

⚡ <b>Full 30-Day Data</b>
Previously only the last 7 days loaded fully. Now the complete 30-day window loads without truncation.

🎨 <b>Freshness Colors</b>
Posted date column now shows:
🟢 Today  🔵 Yesterday  🟡 2–3 days  ⚫ Older

✅ <b>Application Tracker</b>
Track every application through 5 stages: Applied → Screening → Interview → Offer → Rejected. Add notes per job. Export everything to CSV.

🆕 <b>NEW Badge</b>
Jobs you haven't seen before are clearly marked.

🌙 <b>Dark Mode</b>
Full dark mode, system-aware with manual toggle.

🔗 https://job-hunters-rho.vercel.app

⏱ New jobs are added every 2 hours — check back daily to stay ahead.

—
🏢 More companies being added regularly.
Know a company that sponsors H1B or is STEM OPT friendly? Drop a message to the admin and we'll get it added.
"""
# message = """
# 👋 Hello everyone!

# 🔍 <b>Job Hunt Portal</b>  
# https://job-hunters-rho.vercel.app

# 📌 <b>Usage Guide</b>

# • <b>Companies</b> page lists all tracked companies  
# • <b>Latest Jobs</b> shows openings from the last 7 days  
# • Filter by <b>date, title, location, job ID, or company</b>  
# • Sort jobs by <b>posted date</b> or <b>company name</b>  
# • Easy pagination with selectable rows (10, 20, 30, 50, 100)

# 🚀 New jobs are added every <b>4 hours</b>  
# 📅 Check back daily to stay updated

# 💬 <b>Feedback & Requests</b>  
# If you notice issues, have suggestions, or want a company added, feel free to reach out to the admin.

# ☕ <b>Support the Project (Optional)</b>  
# This portal is maintained voluntarily.  
# Tips and support are always appreciated ❤️  
# If you’d like to contribute or know more, drop a message to the admin.

# Happy job hunting and best of luck! 🍀
# """

send_telegram_message(message)
