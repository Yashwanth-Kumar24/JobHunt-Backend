import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://geico.wd1.myworkdayjobs.com/External"
API_URL = "https://geico.wd1.myworkdayjobs.com/wday/cxs/geico/External/jobs"

# Reject senior / leadership / non IC roles
REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|lead|head|architect|principal|"
    r"staff|distinguished|senior\s+manager|"
    r"vice\s*president|president"
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
                "jobFamilyGroup": [
                    "da128ce5a1dc103e7c09aaa3fe312266"
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
            print(f"GEICO page {page + 1}: request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""

            # Reject unwanted roles
            if REJECT_TITLE.search(title):
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = (
                bullet[0]
                if bullet
                else job.get("externalPath", "").split("/")[-1]
            )

            jobs.append({
                "company": "GEICO",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"GEICO page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("GEICO jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("GEICO jobs:", len(res))
    if res:
        print("Sample:", res[0])
