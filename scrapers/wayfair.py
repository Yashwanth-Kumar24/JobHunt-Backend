import re
import requests
from typing import List, Dict

API_URL = "https://www.wayfair.com/a/careers/careers/job_search_data"
BASE_URL = "https://www.wayfair.com/careers/jobs"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://www.wayfair.com",
    "Referer": "https://www.wayfair.com/careers/jobs/?teamIds=1&countryIds=1",
    "x-requested-with": "XMLHttpRequest",
}

# teamId=1 is the Tech/Engineering org; countryId=1 is United States
TEAM_ID = 1
COUNTRY_ID = 1

# Keep only engineering/ML categories; skip PM, UX, Employee Technology (warehouse IT)
KEEP_CATEGORY_IDS = {
    3,   # App Engineering
    6,   # Data Science & Machine Learning
    10,  # Front End Engineering
    11,  # Full Stack Engineering
}

REJECT_TITLE = re.compile(
    r"\b("
    r"senior\s+(?:director|manager|staff)|"
    r"director|manager|head|vp|vice\s*president|president|"
    r"principal|staff|distinguished|fellow|architect|chief|advisor"
    r")\b",
    re.IGNORECASE,
)


def scrape() -> List[Dict]:
    payload = {
        "categoryIds": [],
        "teamIds": [TEAM_ID],
        "locationIds": [],
        "countryIds": [COUNTRY_ID],
        "teamCategoryIds": [],
        "stateIds": [],
        "keywords": "",
        "selectedJobTypeIds": [],
        "updatedFilterPanel": "selectedTeamIds",
    }

    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"Wayfair: request failed - {e}")
        return []
    except ValueError:
        print(f"Wayfair: invalid JSON response, skipping")
        return []

    raw_jobs = data.get("jobListData", [])
    jobs = []
    kept = 0

    for job in raw_jobs:
        # Skip non-engineering categories
        cat_id = (job.get("category") or {}).get("id")
        if cat_id not in KEEP_CATEGORY_IDS:
            continue

        title = (job.get("title") or "").strip()
        if not title or REJECT_TITLE.search(title):
            continue

        job_id = str(job.get("id") or "")
        if not job_id:
            continue

        jobs.append({
            "company": "Wayfair",
            "external_job_id": job_id,
            "job_id": job.get("requisitionId") or job_id,
            "title": title,
            "posting_url": f"{BASE_URL}/{job_id}",
            "posted_at": None,
            "locations": ["Boston, MA, US"],
        })
        kept += 1

    print(f"Wayfair: scanned={len(raw_jobs)} kept={kept}")
    deduped = {j["external_job_id"]: j for j in jobs}
    print("Wayfair jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Total:", len(res))
    if res:
        print("Sample:", res[0])
