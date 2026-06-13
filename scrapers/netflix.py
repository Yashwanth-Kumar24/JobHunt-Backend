import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

API_URL = "https://explore.jobs.netflix.net/api/apply/v2/jobs"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
}

# Netflix levels: 1-4 = new grad to mid, 5 = senior, 6+ = staff/principal
# Title pattern: "Software Engineer 5", "Engineer L4", "- L4", "Frontend Engineer, X - L4"
SENIOR_LEVEL_RE = re.compile(
    r"\b(engineer|developer|scientist|analyst)\s+[56789]\b"
    r"|\b[-–]\s*L[56789]\b"
    r"|\bL[56789]\s*[-–]",
    re.IGNORECASE,
)

REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|head|vp|vice\s*president|president|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief|executive"
    r")\b",
    re.IGNORECASE,
)


def _to_posted_at(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _normalize_location(loc: str) -> str:
    # "New York,New York,United States of America" → "New York, NY"
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}"
    return parts[0] if parts else loc


def scrape(max_pages: int = 10, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    start = 0

    for page in range(1, max_pages + 1):
        params = {
            "domain": "netflix.com",
            "Teams": "Engineering",
            "location": "United States",
            "sort_by": "new",
            "start": start,
            "num": page_size,
        }

        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Netflix page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"Netflix page {page}: invalid JSON")
            break

        positions = data.get("positions", [])
        total = data.get("count", 0)

        if not positions:
            break

        kept = 0
        for pos in positions:
            title = (pos.get("name") or "").strip()
            if not title:
                continue

            # Drop explicit senior/staff levels in title
            if SENIOR_LEVEL_RE.search(title):
                continue

            if REJECT_TITLE.search(title):
                continue

            posted_at = _to_posted_at(pos.get("t_create"))
            if not posted_at or posted_at < cutoff:
                continue

            job_id = pos.get("display_job_id") or str(pos.get("id") or "")
            if not job_id:
                continue

            # Collect US locations only
            raw_locs = pos.get("locations") or [pos.get("location") or ""]
            us_locs = [
                _normalize_location(l) for l in raw_locs
                if "United States" in l
            ]
            if not us_locs:
                continue

            jobs.append({
                "company": "Netflix",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": pos.get("canonicalPositionUrl") or f"https://explore.jobs.netflix.net/careers/job/{pos['id']}",
                "posted_at": posted_at,
                "locations": us_locs,
            })
            kept += 1

        print(f"Netflix page {page}: scanned={len(positions)} kept={kept}")

        if start + page_size >= total:
            break

        start += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Netflix jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total Netflix jobs:", len(res))
    if res:
        for j in res[:5]:
            print(f"  {j['title']} | {j['locations']} | {j['posted_at'].date()}")
