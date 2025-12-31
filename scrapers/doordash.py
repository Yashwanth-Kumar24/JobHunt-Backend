import re
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

SEARCH_URL = (
    "https://careersatdoordash.com/job-search/"
    "?keyword=&location=United%20States"
    "&intern=0"
    "&function=Software%20Engineering%7CData%20Engineering%7CData%20Science"
    "%7CMachine%20Learning%20Engineering%7CSolutions%20Architect"
    "%7CBusiness%20Intelligence%7CQuality%20Assurance"
    "%7CBusiness%20Systems%20Analyst%7CIT%20Support%7C"
    "&spage={page}"
)

ALLOWED_FUNCTIONS = {
    "Software Engineering",
    "Data Engineering",
    "Data Science",
    "Machine Learning Engineering",
    "Solutions Architect",
    "Business Intelligence",
    "Quality Assurance",
    "Business Systems Analyst",
    "IT Support",
}

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|vice president|president"
    r")\b",
    re.IGNORECASE,
)


def scrape(max_pages: int = 5) -> List[Dict]:
    jobs: List[Dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            url = SEARCH_URL.format(page=page_num)
            print(f"Loading DoorDash page {page_num}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.job-item")

            print(f"DoorDash page {page_num}: DOM jobs found: {len(cards)}")

            if not cards:
                break

            for card in cards:
                title_el = card.select_one("div.title-container a")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if REJECT_TITLE.search(title):
                    continue

                href = title_el.get("href", "").strip()
                if not href:
                    continue

                posting_url = href

                job_id_el = card.select_one("div.title-container .label")
                external_job_id = (
                    job_id_el.get_text(strip=True).replace("Job ID:", "").strip()
                    if job_id_el else None
                )

                location_el = card.select_one("div.location-container .value-secondary")
                location = location_el.get_text(strip=True) if location_el else ""

                function_el = card.select_one("div.function-container .value-secondary")
                function = function_el.get_text(strip=True) if function_el else ""

                if function not in ALLOWED_FUNCTIONS:
                    continue

                jobs.append({
                    "company": "DoorDash",
                    "external_job_id": external_job_id,
                    "job_id": external_job_id,
                    "title": title,
                    "posting_url": posting_url,
                    "posted_at": None,
                    "locations": [location] if location else [],
                    "function": function,
                })

            time.sleep(1)

        browser.close()

    deduped = {j["external_job_id"]: j for j in jobs if j["external_job_id"]}
    print("DoorDash jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    results = scrape(max_pages=1)
    print("Total DoorDash jobs:", len(results))
    if results:
        print("Sample:", results[0])
