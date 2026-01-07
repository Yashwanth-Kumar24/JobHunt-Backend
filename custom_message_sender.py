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
👋 Hello everyone!

🔍 <b>Job Hunt Portal</b>  
https://job-hunters-rho.vercel.app

🚀 New jobs are added every <b>2 Hours</b> during business hours.
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
