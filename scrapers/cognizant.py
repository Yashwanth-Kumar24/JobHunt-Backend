import time
import re
import cloudscraper
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timezone, timedelta

BASE_URL = "https://careers.cognizant.com"
SEARCH_URL = "https://careers.cognizant.com/global-en/jobs/"

# Reject only clearly senior / leadership roles
REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|lead|team\s+leader|"
    r"vice\s+president|president|squad\s+leader|architect|customer\s+service"
    r")\b",
    re.IGNORECASE,
)

POSTED_DATE_RE = re.compile(r"(\d{1,2})\s+(\w+)\s+(\d{4})")


def _parse_posted_at(text: str):
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d %b %Y").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    m = POSTED_DATE_RE.search(text)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y").replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _normalize_location(text: str) -> List[str]:
    if not text:
        return []

    text = text.strip()

    # Remove street details if present
    if "-" in text:
        text = text.split("-", 1)[0].strip()

    return [text]


def scrape(max_pages: int = 5, page_size: int = 10) -> List[Dict]:
    jobs: List[Dict] = []

    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False,
        }
    )

    for page in range(max_pages):
        params = {
            "keyword": "",
            "location": "United States",
            "radius": "1000",
            "cname": "United States",
            "ccode": "US",
            "team": [
                "IT Infrastructure",
                "Technology & Engineering",
                "Digital",
            ],
            "pagesize": page_size,
            "page": page,
        }

        r = scraper.get(SEARCH_URL, params=params, timeout=30)

        if r.status_code != 200:
            print(f"Cognizant page {page + 1} blocked: {r.status_code}")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div.card.card-job")

        if not cards:
            break

        kept = 0

        for card in cards:
            external_id = card.get("data-id")
            if not external_id:
                continue

            # Handle both h2 and h3 titles
            title_el = (
                card.select_one("h2.card-title a")
                or card.select_one("h3.card-title a")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # Reject only leadership roles
            if REJECT_TITLE.search(title):
                continue

            href = title_el.get("href", "").strip()
            posting_url = BASE_URL + href if href.startswith("/") else href

            meta_items = card.select("ul.job-meta li")
            location_text = meta_items[0].get_text(strip=True) if meta_items else ""
            date_text = meta_items[1].get_text(strip=True) if len(meta_items) > 1 else ""

            jobs.append({
                "company": "Cognizant",
                "external_job_id": external_id,
                "job_id": external_id,
                "title": title,
                "posting_url": posting_url,
                "posted_at": _parse_posted_at(date_text),
                "locations": _normalize_location(location_text),
            })

            kept += 1

        print(
            f"Cognizant page {page + 1}: "
            f"scanned={len(cards)} kept={kept}"
        )

        # Gentle delay to avoid rate limits
        time.sleep(1.0)

    # Deduplicate by external_job_id
    deduped = {}
    for j in jobs:
        deduped[j["external_job_id"]] = j

    results = list(deduped.values())
    print("Cognizant jobs:", len(results))
    return results


if __name__ == "__main__":
    results = scrape(max_pages=5)
    print("Total Cognizant jobs:", len(results))
    if results:
        print("Sample:", results[0])
