import re
from typing import List, Dict
from playwright.sync_api import sync_playwright

CAREERS_URL = "https://www.wayfair.com/careers/jobs?teamIds=1&countryIds=1"
API_PATH = "/a/careers/careers/job_search_data"
BASE_URL = "https://www.wayfair.com/careers/jobs"

# Keep only engineering/ML categories; skip PM, UX, Employee Technology
KEEP_CATEGORY_IDS = {
    3,   # App Engineering
    6,   # Data Science & Machine Learning
    10,  # Front End Engineering
    11,  # Full Stack Engineering
}

REJECT_TITLE = re.compile(
    r"\b("
    r"senior\s+(?:director|manager|staff)|"
    r"director|manager|head|vp|vice\s*president|president|"
    r"principal|staff|distinguished|fellow|architect|chief|advisor"
    r")\b",
    re.IGNORECASE,
)


def scrape() -> List[Dict]:
    jobs: List[Dict] = []
    api_data = {}

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
                "Chrome/148.0.0.0 Safari/537.36"
            )
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page = context.new_page()

        # Intercept the jobs API response
        def handle_response(response):
            if API_PATH in response.url and response.status == 200:
                try:
                    api_data["jobs"] = response.json().get("jobListData", [])
                except Exception:
                    pass

        page.on("response", handle_response)

        print("Wayfair: loading careers page via Playwright...")
        page.goto(CAREERS_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        browser.close()

    raw_jobs = api_data.get("jobs", [])
    if not raw_jobs:
        print("Wayfair: no jobs captured from API response")
        return []

    kept = 0
    for job in raw_jobs:
        cat_id = (job.get("category") or {}).get("id")
        if cat_id not in KEEP_CATEGORY_IDS:
            continue

        title = (job.get("title") or "").strip()
        if not title or REJECT_TITLE.search(title):
            continue

        job_id = str(job.get("id") or "")
        if not job_id:
            continue

        jobs.append({
            "company": "Wayfair",
            "external_job_id": job_id,
            "job_id": job.get("requisitionId") or job_id,
            "title": title,
            "posting_url": f"{BASE_URL}/{job_id}",
            "posted_at": None,
            "locations": ["Boston, MA, US"],
        })
        kept += 1

    print(f"Wayfair: scanned={len(raw_jobs)} kept={kept}")
    deduped = {j["external_job_id"]: j for j in jobs}
    print("Wayfair jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total:", len(res))
    if res:
        print("Sample:", res[0])
