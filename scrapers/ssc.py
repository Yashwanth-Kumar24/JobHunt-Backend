import re
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict

BASE_URL = "https://wd1.myworkdaysite.com/en-US/recruiting/ssctech/SSCTechnologies"
API_URL = "https://wd1.myworkdaysite.com/wday/cxs/ssctech/SSCTechnologies/jobs"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|team\s*leader|"
    r"vice\s*president|president|squad\s*leader"
    r")\b",
    re.IGNORECASE,
)

ACCEPT_TITLE = re.compile(
    r"\b("
    r"software\s+engineer|software\s+developer|"
    r"software|engineer|developer"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)


def _parse_posted_at(posted_on: str):
    if not posted_on:
        return None

    text = posted_on.strip().lower()

    if text == "posted today":
        return datetime.utcnow()

    if text == "posted yesterday":
        return datetime.utcnow() - timedelta(days=1)

    m = POSTED_DAYS_RE.search(posted_on)
    if m:
        return datetime.utcnow() - timedelta(days=int(m.group(1)))

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
        except requests.exceptions.RequestException as e:
            print(f"SS&C page {page + 1}: Request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""
            
            # First check if title matches our accept filter
            if not ACCEPT_TITLE.search(title):
                continue
            
            # Then check if title matches reject filter
            if REJECT_TITLE.search(title):
                continue

            bullet = job.get("bulletFields") or []
            if not bullet:
                # Use a different field as fallback for external_job_id
                external_path = job.get("externalPath", "")
                if external_path:
                    # Extract job ID from path like "/job/Software-Engineer/JR12345"
                    external_job_id = external_path.split("/")[-1] if "/" in external_path else external_path
                else:
                    # Fallback to title-based ID
                    external_job_id = title.replace(" ", "-")[:50]
            else:
                external_job_id = bullet[0]

            jobs.append({
                "company": "SS&C Technologies",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"SS&C page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)
    
    # Final dedupe by external_job_id
    deduped = {j["external_job_id"]: j for j in jobs}
    print("SS&C jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("SS&C jobs:", len(res))
    if res:
        print("Sample:", res[0])