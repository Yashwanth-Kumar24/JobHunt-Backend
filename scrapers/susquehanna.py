import time
import requests
from datetime import datetime, timezone
from typing import List, Dict

API_URL = "https://careers.sig.com/widgets"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://careers.sig.com",
    "Referer": "https://careers.sig.com/search-results",
}

CATEGORIES = [
    "Technology - Software Engineering",
    "Technology - Infrastructure, Support + Engineering"
]

LOCATIONS = [
    "Bala Cynwyd (Philadelphia Area), Pennsylvania United States",
    "New York, New York United States",
]

PAGE_SIZE = 10


def _parse_posted_at(posted_date: str):
    if not posted_date:
        return None
    try:
        # Example: 2026-01-05T00:06:35.502+0000
        return datetime.strptime(posted_date, "%Y-%m-%dT%H:%M:%S.%f%z")
    except Exception:
        return None


def scrape(max_pages: int = 5) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "lang": "en_us",
            "deviceType": "desktop",
            "country": "us",
            "pageName": "search-results",
            "ddoKey": "refineSearch",
            "from": offset,
            "size": PAGE_SIZE,
            "keywords": "",
            "jobs": True,
            "counts": True,
            "clearAll": False,
            "global": True,
            "siteType": "external",
            "jdsource": "facets",
            "sortBy": "Most recent",
            "sort": {"field": "postedDate", "order": "desc"},
            "selected_fields": {
                "category": CATEGORIES,
                "location": LOCATIONS,
            },
            "all_fields": ["category", "location", "type", "jobtypevalue"],
        }

        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"SIG page {page + 1}: request failed - {e}")
            break

        data = r.json()
        jobs_data = data.get("refineSearch", {}).get("data", {}).get("jobs", [])

        if not jobs_data:
            break

        print(f"SIG page {page + 1}: received {len(jobs_data)} jobs")

        for job in jobs_data:
            job_id = job.get("jobId")
            title = job.get("title")
            location = job.get("location")
            posted_date = job.get("postedDate")

            if not job_id or not title:
                continue

            jobs.append({
                "company": "Susquehanna International Group",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": job.get("applyUrl"),
                "posted_at": _parse_posted_at(posted_date),
                "locations": [location] if location else [],
            })

        offset += PAGE_SIZE
        time.sleep(0.3)

    deduped = {j["job_id"]: j for j in jobs}
    print("SIG jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("Total SIG jobs:", len(res))
    if res:
        print("Sample:", res[0])
    for x in res:
        print(x)
