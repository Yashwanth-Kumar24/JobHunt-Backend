import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://lilly.wd5.myworkdayjobs.com/en-US/LLY"
API_URL = "https://lilly.wd5.myworkdayjobs.com/wday/cxs/lilly/LLY/jobs"

# Reject senior / leadership / non IC roles
REJECT_TITLE = re.compile(
    r"\b("
    r"principal|staff|director|manager|head|lead|vp|vice\s*president|"
    r"senior\s+manager|advisor|senior\s+director|distinguished|architect"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)
POSTED_30_PLUS_RE = re.compile(r"Posted\s+30\+\s+Days?\s+Ago", re.IGNORECASE)


def _parse_posted_at(posted_on: str):
    if not posted_on:
        return None

    now = datetime.now(timezone.utc)
    text = posted_on.strip().lower()

    if text == "posted today":
        return now

    if text == "posted yesterday":
        return now - timedelta(days=1)

    if POSTED_30_PLUS_RE.search(posted_on):
        return now - timedelta(days=30)

    m = POSTED_DAYS_RE.search(posted_on)
    if m:
        return now - timedelta(days=int(m.group(1)))

    return None


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []
    return [loc_text.strip()]


def scrape(max_pages: int = 15, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    
    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "jobFamilyGroup": ["99c6e09d03e80198acd7817ff04af833"],
                "locationCountry": ["bc33aa3152ec42d4995f4791a106ed09"]
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Lilly page {page + 1}: request failed - {e}")
            break

        data = r.json()
        
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        for job in postings:
            title = job.get("title") or ""
            
            posted_at = _parse_posted_at(job.get("postedOn"))

            # Reject unwanted roles
            if REJECT_TITLE.search(title):
                continue

            # Drop jobs older than 30 days or unknown dates
            if not posted_at or posted_at < cutoff_date:
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = (
                bullet[0]
                if bullet
                else job.get("externalPath", "").split("/")[-1]
            )

            jobs.append({
                "company": "Eli Lilly",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": posted_at,
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"Lilly page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Lilly jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Lilly jobs:", len(res))
    if res:
        print("Sample:", res[0])
