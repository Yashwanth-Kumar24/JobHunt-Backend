import re
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict

BASE_URL = "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site"
API_URL = "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs"

# Reject only these roles (senior and sr are allowed)
REJECT_TITLE = re.compile(
    r"\b("
    r"manager|principal|lead|architect"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)


def _parse_posted_at(posted_on: str):
    if not posted_on:
        return None

    m = POSTED_DAYS_RE.search(posted_on)
    if not m:
        return None

    days = int(m.group(1))
    return datetime.utcnow() - timedelta(days=days)


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []

    # Example: "2 Locations"
    if "Locations" in loc_text:
        return [loc_text.strip()]

    # Example: "Indiana - Indianapolis"
    if "-" in loc_text:
        return [loc_text.split("-", 1)[-1].strip()]

    return [loc_text.strip()]


def scrape(max_pages: int = 20, page_size: int = 20) -> List[Dict]:
    """
    Scrape Salesforce jobs using Workday API.
    Returns list of normalized job dicts.
    """

    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                # United States of America
                "CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended": [
                    "bc33aa3152ec42d4995f4791a106ed09"
                ],
                # Software Engineering job family
                "jobFamilyGroup": [
                    "14fa3452ec7c1011f90d0002a2100000"
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
            if REJECT_TITLE.search(title):
                continue

            bullet_fields = job.get("bulletFields") or []
            if not bullet_fields:
                continue

            external_job_id = bullet_fields[0]

            posting_url = BASE_URL + job.get("externalPath", "")
            locations_text = job.get("locationsText")
            locations = _normalize_locations(locations_text)

            posted_at = _parse_posted_at(job.get("postedOn"))

            jobs.append({
                "company": "Salesforce",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": posting_url,
                "posted_at": posted_at,
                "locations": locations,
            })

            kept += 1

        print(
            f"Salesforce page {page + 1}: "
            f"scanned={len(postings)} kept={kept}"
        )

        offset += page_size
        time.sleep(0.4)
    deduped = {}
    for job in jobs:
        deduped[job["external_job_id"]] = job
    print("Salesforce jobs:", len(list(deduped.values())))
    return list(deduped.values())


if __name__ == "__main__":
    results = scrape(max_pages=5)
    print("Total Salesforce jobs:", len(results))
    if results:
        print("Sample:", results[0])
