import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

# Real API endpoint — GET with query params (not POST to /widgets)
API_URL = "https://careers.sig.com/api/jobs"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Referer": "https://careers.sig.com/global-experienced/jobs",
}

# Pipe-separated tags — maps to technology roles
TAGS1 = "Technology - Software Engineering|Technology - Infrastructure, Support + Engineering"

# Pipe-separated city,state,country strings
LOCATIONS = "|".join([
    "Bala Cynwyd (Philadelphia Area),Pennsylvania,United States",
    "Chicago,Illinois,United States",
    "New York,New York,United States",
])

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow"
    r")\b",
    re.IGNORECASE,
)

PAGE_SIZE = 10


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("+0000", "+00:00"))
    except Exception:
        return None


def scrape(max_pages: int = 5) -> List[Dict]:
    jobs: List[Dict] = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    for page in range(1, max_pages + 1):
        params = {
            "tags1":      TAGS1,
            "page":       page,
            "locations":  LOCATIONS,
            "sortBy":     "posted_date",
            "descending": "true",
            "internal":   "false",
            "domain":     "sig.jibeapply.com",
        }

        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"SIG page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"SIG page {page}: invalid JSON, skipping")
            break

        # Response: {"jobs": [{"data": {...}}, ...]}
        job_list = data.get("jobs", [])
        if not job_list:
            break

        kept = 0
        stop_early = False

        for item in job_list:
            j = item.get("data", {})

            title = (j.get("title") or "").strip()
            if not title or REJECT_TITLE.search(title):
                continue

            # US only
            if (j.get("country_code") or "").upper() != "US":
                continue

            posted_at = _parse_posted_at(j.get("posted_date"))
            if not posted_at or posted_at < cutoff_date:
                stop_early = True
                break

            req_id = str(j.get("req_id") or j.get("slug") or "")
            if not req_id:
                continue

            city  = j.get("city") or ""
            state = j.get("state") or ""
            loc   = f"{city}, {state}, US" if city and state else (city or state or "US")

            jobs.append({
                "company":         "Susquehanna International Group",
                "external_job_id": req_id,
                "job_id":          req_id,
                "title":           title,
                "posting_url":     f"https://careers.sig.com/job/{req_id}",
                "posted_at":       posted_at,
                "locations":       [loc],
            })
            kept += 1

        print(f"SIG page {page}: scanned={len(job_list)} kept={kept}")

        if stop_early or len(job_list) < PAGE_SIZE:
            break

        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("SIG jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Total SIG jobs:", len(res))
    if res:
        print("Sample:", res[0])
