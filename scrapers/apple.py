import time
import requests
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict

API_URL = "https://jobs.apple.com/api/v1/search"
BASE_POSTING_URL = "https://jobs.apple.com/en-us/details"

# Reject senior leadership / non IC roles
REJECT_TITLE = re.compile(
    r"\b("
    r"director|senior\s+director|principal|staff|manager|head|lead|senior|operations|sr|evaluation|"
    r"vp|vice\s*president|distinguished|fellow|soc|power|sales|embedded|government|producer|"
    r"wireless|rfic|silicon|estate|hardware|ddr|retail"
    r")\b",
    re.IGNORECASE,
)

HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "browserlocale": "en-us",
    "accept-language": "en-US,en;q=0.9",
}

SEARCH_PAYLOAD_BASE = {
    "query": "",
    "filters": {
        "keywords": ["software", "devops", "data", "ai", "cloud"],
        "locations": ["postLocation-USA"],
    },
    "locale": "en-us",
    "sort": "newest",
    "format": {
        "longDate": "MMMM D, YYYY",
        "mediumDate": "MMM D, YYYY",
    },
}


def _parse_posted_at(post_date_gmt: str):
    if not post_date_gmt:
        return None
    return datetime.fromisoformat(
        post_date_gmt.replace("Z", "+00:00")
    )


def scrape(max_pages: int = 10, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []

    for page in range(1, max_pages + 1):
        payload = SEARCH_PAYLOAD_BASE.copy()
        payload["page"] = page

        try:
            r = requests.post(
                API_URL,
                json=payload,
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Apple page {page}: request failed - {e}")
            break

        data = r.json()
        results = data.get("res", {}).get("searchResults", [])

        if not results:
            break

        kept = 0

        for job in results:
            title = job.get("postingTitle", "")
            if not title:
                continue

            if REJECT_TITLE.search(title):
                continue

            job_id = job.get("id")
            if not job_id:
                continue

            locations = [
                loc.get("name")
                for loc in job.get("locations", [])
                if loc.get("name")
            ]

            posted_at = _parse_posted_at(job.get("postDateInGMT"))

            jobs.append({
                "company": "Apple",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": f"{BASE_POSTING_URL}/{job_id}",
                "posted_at": posted_at,
                "locations": locations,
            })

            kept += 1

        print(
            f"Apple page {page}: "
            f"scanned={len(results)} kept={kept}"
        )

        time.sleep(0.4)

    # Deduplicate by job_id
    deduped = {j["external_job_id"]: j for j in jobs}
    results = list(deduped.values())
    print("Apple jobs:", len(results))
    return results


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Apple jobs:", len(res))
    if res:
        print("Sample:", res[0])
