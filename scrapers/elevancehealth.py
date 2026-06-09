import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://elevancehealth.wd1.myworkdayjobs.com/ANT/jobs"
API_URL = "https://elevancehealth.wd1.myworkdayjobs.com/wday/cxs/elevancehealth/ANT/jobs"

# IT/Technology job family group from network capture
JOB_FAMILY_GROUP = ["f42bff05a414010057201f1c4a500000"]

REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|lead|leader|architect|principal|staff|distinguished|fellow|"
    r"advisor|head|vp|vice\s*president|president|chief|consultant|supervisor|"
    r"sr\.?\s+director|senior\s+director"
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


def _is_us_location(loc_text: str) -> bool:
    if not loc_text:
        return False
    text = loc_text.lower()
    return "us" in text or "united states" in text or "locations" in text or "remote" in text


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []
    if re.match(r"^\d+\s+locations?$", loc_text.strip(), re.IGNORECASE):
        return []
    return [loc_text.strip()]


def scrape(max_pages: int = 10, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {"jobFamilyGroup": JOB_FAMILY_GROUP},
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Elevance Health page {page + 1}: request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0
        for job in postings:
            title = job.get("title") or ""
            locations_text = job.get("locationsText") or ""

            if not _is_us_location(locations_text):
                continue

            if REJECT_TITLE.search(title):
                continue

            posted_at = _parse_posted_at(job.get("postedOn"))
            if posted_at and posted_at < datetime.now(timezone.utc) - timedelta(days=30):
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = bullet[0] if bullet else job.get("externalPath", "").split("_")[-1]

            jobs.append({
                "company": "Elevance Health",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": posted_at,
                "locations": _normalize_locations(locations_text),
            })
            kept += 1

        print(f"Elevance Health page {page + 1}: scanned={len(postings)} kept={kept}")

        if len(postings) < page_size:
            break

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Elevance Health jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("Total:", len(res))
    if res:
        print("Sample:", res[0])
