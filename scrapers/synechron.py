import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://synechron.wd1.myworkdayjobs.com/en-US/SynechronCareers"
API_URL = "https://synechron.wd1.myworkdayjobs.com/wday/cxs/synechron/SynechronCareers/jobs"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|head|vice\s*president|president|expert"
    r"chief|squad\s*leader|lead|master|owner"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)
POSTING_DATE_RE = re.compile(r"Posting Date:\s*(\d{2}/\d{2}/\d{4})")


def _parse_posted_at(posted_on: str, bullet_fields: List[str]):
    now = datetime.now(timezone.utc)

    if posted_on:
        text = posted_on.strip().lower()

        if text == "posted today":
            return now

        if text == "posted yesterday":
            return now - timedelta(days=1)

        m = POSTED_DAYS_RE.search(posted_on)
        if m:
            return now - timedelta(days=int(m.group(1)))

    for field in bullet_fields or []:
        m = POSTING_DATE_RE.search(field)
        if m:
            dt = datetime.strptime(m.group(1), "%m/%d/%Y")
            return dt.replace(tzinfo=timezone.utc)

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
                "jobFamilyGroup": [
                    "b1511063925e1000a71e29c048600000"
                ],
                "locationCountry": [
                    "bc33aa3152ec42d4995f4791a106ed09"  # United States
                ]
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Synechron page {page + 1}: request failed - {e}")
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

            bullet = job.get("bulletFields") or []
            external_job_id = bullet[0] if bullet else job.get("externalPath", "").split("/")[-1]

            jobs.append({
                "company": "Synechron",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn"), bullet),
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"Synechron page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Synechron jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("Synechron jobs:", len(res))
    if res:
        print("Sample:", res[0])
