import re
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict

BASE_URL = "https://fmr.wd1.myworkdayjobs.com/FidelityCareers"
API_URL = "https://fmr.wd1.myworkdayjobs.com/wday/cxs/fmr/FidelityCareers/jobs"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|team\s*leader|"
    r"vice\s*president|president|squad\s*leader|leader"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)

def _parse_posted_at(posted_on: str):
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

    return None


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []

    if "locations" in loc_text.lower():
        return [loc_text.strip()]

    if "-" in loc_text:
        return [loc_text.split("-", 1)[-1].strip()]

    return [loc_text.strip()]


def scrape(max_pages: int = 20, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "locationCountry": [
                    "bc33aa3152ec42d4995f4791a106ed09"
                ],
                "jobFamilyGroup": [
                    "e39fd413f80c0104eb5775256a997b12"
                ],
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        r = requests.post(API_URL, json=payload, timeout=30)
        r.raise_for_status()

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""
            if not title:
                continue
            if REJECT_TITLE.search(title):
                continue

            bullet = job.get("bulletFields") or []
            if not bullet:
                continue

            external_job_id = bullet[0]
            
            jobs.append({
                "company": "Fidelity Investments",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(job.get("locationsText")),
                "page":page
            })
            kept += 1

        print(f"Fidelity page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)
    # Final dedupe by external_job_id
    deduped = {j["external_job_id"]: j for j in jobs}
    print("Fidelity jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Fidelity jobs:", len(res))
    if res:
        print("Sample:", res[0])
    for x in res:
        print(x)
