import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

API_URL = "https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
}

US_OFFICE_ID = 4024285004  # "US" office node

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief"
    r")\b",
    re.IGNORECASE,
)


def _parse_updated_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).astimezone(timezone.utc)
    except Exception:
        return None


def _is_engineering(departments: list) -> bool:
    return any((d.get("name") or "").lower() == "engineering" for d in departments)


def _is_us(offices: list) -> bool:
    for o in offices:
        if o.get("id") == US_OFFICE_ID:
            return True
        # also catch child offices whose parent is the US node
        if o.get("parent_id") == US_OFFICE_ID:
            return True
    return False


def scrape() -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    try:
        r = requests.get(API_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"Figma: request failed - {e}")
        return []
    except ValueError:
        print("Figma: invalid JSON")
        return []

    raw_jobs = data.get("jobs", [])
    jobs = []
    kept = 0

    for job in raw_jobs:
        # Engineering department only
        departments = job.get("departments") or []
        if not _is_engineering(departments):
            continue

        # US offices only
        offices = job.get("offices") or []
        if not _is_us(offices):
            continue

        title = (job.get("title") or "").strip()
        if not title or REJECT_TITLE.search(title):
            continue

        updated_at = _parse_updated_at(job.get("updated_at"))
        if not updated_at or updated_at < cutoff:
            continue

        job_id = str(job.get("id") or "")
        if not job_id:
            continue

        location_name = (job.get("location") or {}).get("name") or ""

        jobs.append({
            "company": "Figma",
            "external_job_id": job_id,
            "job_id": job_id,
            "title": title,
            "posting_url": job.get("absolute_url") or f"https://boards.greenhouse.io/figma/jobs/{job_id}",
            "posted_at": updated_at,
            "locations": [location_name] if location_name else [],
        })
        kept += 1

    print(f"Figma: scanned={len(raw_jobs)} kept={kept}")
    deduped = {j["external_job_id"]: j for j in jobs}
    print("Figma jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total Figma jobs:", len(res))
    if res:
        for j in res[:5]:
            print(f"  {j['title']} | {j['locations']} | {j['posted_at'].date()}")
