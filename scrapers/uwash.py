import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://wd5.myworkdaysite.com"
API_URL = "https://wd5.myworkdaysite.com/wday/cxs/uw/uwhires/jobs"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|team\s*leader|"
    r"vice\s*president|president|squad\s*leader"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)
POSTING_DATE_RE = re.compile(r"Posting Date:\s*(\d{2}/\d{2}/\d{4})")


def _parse_posted_at(posted_on: str, bullet_fields: List[str]):
    if not posted_on:
        return None

    now = datetime.now(timezone.utc)
    text = posted_on.strip().lower()

    if text == "posted today":
        return now

    if text == "posted yesterday":
        return now - timedelta(days=1)

    m = POSTED_DAYS_RE.search(posted_on)
    if m:
        return now - timedelta(days=int(m.group(1)))

    # Handle "Posted 30+ Days Ago" via Posting Date
    for field in bullet_fields or []:
        m2 = POSTING_DATE_RE.search(field)
        if m2:
            return datetime.strptime(
                m2.group(1), "%m/%d/%Y"
            ).replace(tzinfo=timezone.utc)

    return None


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []

    return [loc_text.strip()]


def scrape(max_pages: int = 20, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "jobFamily": ["5e955a616fd51001a3042cc61f7e0000"]
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"UW page {page + 1}: request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""
            if REJECT_TITLE.search(title):
                continue

            bullet_fields = job.get("bulletFields") or []
            external_job_id = bullet_fields[0]

            jobs.append({
                "company": "University of Washington",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn"), bullet_fields),
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"UW page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("UW jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("UW jobs:", len(res))
    if res:
        print("Sample:", res[0])