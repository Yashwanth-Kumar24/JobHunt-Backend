import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

API_URL = "https://careers.amd.com/api/jobs"
BASE_URL = "https://careers.amd.com/careers-home/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://careers.amd.com/careers-home/jobs",
}

REJECT_TITLE = re.compile(
    r"\b("
    r"staff|principal|director|manager|head|lead|vp|vice\s*president|"
    r"president|architect|distinguished|fellow|advisor|consultant"
    r")\b",
    re.IGNORECASE,
)


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("+0000", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def scrape(max_pages: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "country": "United States",
            "categories": "Engineering",
            "sortBy": "posted_date",
            "descending": "true",
            "internal": "false",
        }

        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"AMD page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"AMD page {page}: invalid JSON response, skipping")
            break

        raw_jobs = data.get("jobs", [])
        if not raw_jobs:
            break

        kept = 0
        for item in raw_jobs:
            job = item.get("data") or {}

            title = (job.get("title") or "").strip()
            if not title or REJECT_TITLE.search(title):
                continue

            posted_at = _parse_posted_at(job.get("posted_date"))
            if not posted_at or posted_at < cutoff:
                break  # sorted by date desc, so no point continuing

            req_id = str(job.get("req_id") or job.get("slug") or "")
            if not req_id:
                continue

            city = job.get("city") or ""
            state = job.get("state") or ""
            location = ", ".join(p for p in [city, state, "US"] if p)

            jobs.append({
                "company": "AMD",
                "external_job_id": req_id,
                "job_id": req_id,
                "title": title,
                "posting_url": f"{BASE_URL}/{req_id}",
                "posted_at": posted_at,
                "locations": [location] if location else [],
            })
            kept += 1

        print(f"AMD page {page}: scanned={len(raw_jobs)} kept={kept}")

        if kept == 0 and page > 1:
            break

        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("AMD jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("AMD jobs:", len(res))
    if res:
        print("Sample:", res[0])
