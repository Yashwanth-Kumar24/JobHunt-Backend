import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

# Matches "San Francisco, CA" / "New York, NY" etc.
_US_STATE_RE = re.compile(
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    r"MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b",
    re.IGNORECASE,
)

# One entry per company: (display_name, greenhouse_token, departments_to_keep)
# departments_to_keep: set of lowercase substrings — job kept if any match dept name
# Pass None to keep all Engineering-like departments
COMPANIES = [
    ("Stripe",               "stripe",             {"engineering", "infrastructure", "data"}),
    ("Databricks",           "databricks",          {"engineering", "infrastructure", "data", "ml", "platform"}),
    ("Airbnb",               "airbnb",              {"engineering", "data", "infrastructure"}),
    ("Lyft",                 "lyft",                {"engineering", "data", "infrastructure", "platform"}),
    ("Pinterest",            "pinterest",           {"engineering", "data", "infrastructure"}),
    ("Robinhood",            "robinhood",           {"engineering", "data", "infrastructure", "platform"}),
    ("Datadog",              "datadog",             {"engineering", "data", "infrastructure", "platform"}),
    ("MongoDB",              "mongodb",             {"engineering", "data", "infrastructure", "platform"}),
    ("Instacart",            "instacart",           {"engineering", "data", "infrastructure", "platform"}),
    ("Palo Alto Networks",   "paloaltonetworks",    {"engineering", "data", "infrastructure", "cloud", "security"}),
    ("Dropbox",              "dropbox",             {"engineering", "data", "infrastructure"}),
]

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief"
    r")\b",
    re.IGNORECASE,
)


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _is_us_location(location_name: str) -> bool:
    if not location_name:
        return False
    text = location_name.lower()
    return (
        "united states" in text
        or ", us" in text
        or text.endswith(" us")
        or "remote" in text
        or "usa" in text
        or bool(_US_STATE_RE.search(location_name))  # "San Francisco, CA" etc.
    )


def _dept_matches(departments: List[Dict], keep_set) -> bool:
    if keep_set is None:
        return True
    # If no department info available, don't reject — title filter is enough
    if not departments:
        return True
    for dept in departments:
        name = (dept.get("name") or "").lower()
        if any(kw in name for kw in keep_set):
            return True
    return False


def _scrape_company(company_name: str, token: str, keep_depts) -> List[Dict]:
    url = GREENHOUSE_API.format(token=token)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"{company_name}: request failed - {e}")
        return []
    except ValueError:
        print(f"{company_name}: invalid JSON response")
        return []

    raw_jobs = data.get("jobs", [])
    jobs = []
    kept = 0

    for job in raw_jobs:
        title = (job.get("title") or "").strip()
        if not title or REJECT_TITLE.search(title):
            continue

        # Department filter
        departments = job.get("departments") or []
        if not _dept_matches(departments, keep_depts):
            continue

        # Location — US only
        location_name = (job.get("location") or {}).get("name") or ""
        if not _is_us_location(location_name):
            continue

        posted_at = _parse_posted_at(job.get("updated_at"))
        if not posted_at or posted_at < cutoff:
            continue

        job_id = str(job.get("id") or "")
        if not job_id:
            continue

        jobs.append({
            "company": company_name,
            "external_job_id": job_id,
            "job_id": job_id,
            "title": title,
            "posting_url": job.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{job_id}",
            "posted_at": posted_at,
            "locations": [location_name] if location_name else [],
        })
        kept += 1

    print(f"{company_name}: scanned={len(raw_jobs)} kept={kept}")
    return jobs


def scrape() -> List[Dict]:
    all_jobs: List[Dict] = []

    for company_name, token, keep_depts in COMPANIES:
        company_jobs = _scrape_company(company_name, token, keep_depts)
        all_jobs.extend(company_jobs)
        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in all_jobs}
    print(f"Greenhouse total jobs: {len(deduped)}")
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total:", len(res))
    if res:
        print("Sample:", res[0])
