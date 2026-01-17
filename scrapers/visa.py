import re
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict

API_URL = "https://search.visa.com/CAREERS/careers/jobs?q="
REFERER = "https://corporate.visa.com/en/jobs/"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|team\s*leader|chief|athelets|legal|service|executive"
    r"vice\s*president|president|mba|sales|accountant|accounting|staff|pricing|counsel|owner"
    r")\b",
    re.IGNORECASE,
)


def _normalize_locations(job: Dict) -> List[str]:
    parts = [
        job.get("city"),
        job.get("region"),
        job.get("country"),
    ]
    loc = ", ".join(p for p in parts if p)
    return [loc] if loc else []


def _parse_posted_at(created_on: str):
    if not created_on:
        return None

    try:
        return datetime.fromisoformat(
            created_on.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return None


def scrape(page_size: int = 1000) -> List[Dict]:
    jobs: List[Dict] = []

    payload = {
        "filters": [],
        "city": [
            "Ashburn",
            "Atlanta",
            "Austin",
            "Bellevue",
            "Denver",
            "Foster",
            "Foster City",
            "Highlands Ranch",
            "Los Angeles",
            "Miami",
            "New York",
            "San Francisco",
            "San Juan",
            "Union City",
            "Washington",
        ],
        "from": 0,
        "size": page_size,
        "sort": {"createdOn": "DESC"},
    }

    headers = {
        "Content-Type": "application/json",
        "Referer": REFERER,
    }

    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Visa request failed: {e}")
        return []

    data = r.json()
    postings = data.get("jobDetails", [])
    kept = 0

    for job in postings:
        title = job.get("jobTitle") or ""
        if REJECT_TITLE.search(title):
            continue

        external_job_id = job.get("refNumber")

        jobs.append({
            "company": "Visa",
            "external_job_id": external_job_id,
            "job_id": external_job_id,
            "title": title,
            "posting_url": f"{REFERER}{external_job_id}",
            "posted_at": _parse_posted_at(job.get("createdOn")),
            "locations": _normalize_locations(job),
        })

        kept += 1

    print(f"Visa: scanned={len(postings)} kept={kept}")

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Visa jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Visa jobs:", len(res))
    if res:
        print("Sample:", res[0])