import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

API_URL = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://www.uber.com",
    "Referer": "https://www.uber.com/us/en/careers/list/",
    "x-csrf-token": "x",
}

# Uber levels: L3=new grad, L4=junior, L5=mid, L5B/L6+=senior/staff
KEEP_LEVELS = {"3", "4", "5"}

# US locations — API expects objects, NOT strings
US_LOCATIONS = [
    {"country": "USA", "region": "California",        "city": "San Francisco"},
    {"country": "USA", "region": "California",        "city": "Sunnyvale"},
    {"country": "USA", "region": "California",        "city": "Los Angeles"},
    {"country": "USA", "region": "New York",          "city": "New York"},
    {"country": "USA", "region": "Washington",        "city": "Seattle"},
    {"country": "USA", "region": "Illinois",          "city": "Chicago"},
    {"country": "USA", "region": "Texas",             "city": "Dallas"},
    {"country": "USA", "region": "Colorado",          "city": "Denver"},
    {"country": "USA", "region": "Georgia",           "city": "Atlanta"},
    {"country": "USA", "region": "Massachusetts",     "city": "Boston"},
    {"country": "USA", "region": "Florida",           "city": "Miami"},
    {"country": "USA", "region": "Arizona",           "city": "Phoenix"},
    {"country": "USA", "region": "Tennessee",         "city": "Nashville"},
]

REJECT_TITLE = re.compile(
    r"\b("
    r"senior\s+staff|senior\s+director|staff|principal|director|"
    r"head|vp|vice\s*president|president|distinguished|fellow"
    r")\b",
    re.IGNORECASE,
)

PAGE_SIZE = 10


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _normalize_locations(job: Dict) -> List[str]:
    locs = job.get("allLocations") or []
    if locs:
        result = []
        for loc in locs:
            if loc.get("countryName") != "United States":
                continue
            city = loc.get("city", "")
            region = loc.get("region", "")
            parts = [p for p in [city, region, "US"] if p]
            result.append(", ".join(parts))
        return result
    primary = job.get("location") or {}
    city = primary.get("city", "")
    region = primary.get("region", "")
    parts = [p for p in [city, region, "US"] if p]
    return [", ".join(parts)] if parts else []


def scrape(max_pages: int = 15, page_size: int = PAGE_SIZE) -> List[Dict]:
    jobs: List[Dict] = []
    page = 0  # Uber API is 0-indexed

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    while page < max_pages:
        payload = {
            "limit": page_size,
            "page": page,
            "params": {
                "department": ["Engineering", "Data Science"],
                "location": US_LOCATIONS,
                "lineOfBusinessName": [],
                "programAndPlatform": [],
                "team": [],
            },
        }

        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Uber page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"Uber page {page}: invalid JSON response, skipping")
            break

        results = data.get("data", {}).get("results", [])
        if not results:
            print(f"Uber page {page}: no results. Top-level keys: {list(data.keys())}, data keys: {list((data.get('data') or {}).keys())}")
            break

        kept = 0
        for job in results:
            # Filter by level — only keep L3/L4/L5
            level = str(job.get("level") or "")
            if level not in KEEP_LEVELS:
                continue

            title = (job.get("title") or "").strip()
            if not title:
                continue

            # Belt-and-suspenders title check for anything that slips through level filter
            if REJECT_TITLE.search(title):
                continue

            # US only
            primary_country = (job.get("location") or {}).get("country", "")
            if primary_country != "USA":
                continue

            posted_at = _parse_posted_at(job.get("creationDate"))
            if not posted_at or posted_at < cutoff_date:
                continue

            job_id = str(job.get("id") or "")
            if not job_id:
                continue

            jobs.append({
                "company": "Uber",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": f"https://www.uber.com/us/en/careers/list/{job_id}/",
                "posted_at": posted_at,
                "locations": _normalize_locations(job),
            })
            kept += 1

        print(f"Uber page {page}: scanned={len(results)} kept={kept}")

        if len(results) < page_size:
            break

        page += 1
        time.sleep(0.6)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Uber jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Uber jobs:", len(res))
    if res:
        print("Sample:", res[0])
