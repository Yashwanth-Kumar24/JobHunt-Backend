import re
import time
import requests
from datetime import datetime
from typing import List, Dict

AMAZON_SEARCH_URL = "https://www.amazon.jobs/en/search.json"

# Reject only senior / leadership roles
REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|lead|manager|architect|staff|sdm|director|"
    r"sde\s*(iii|3|iv|4|v|5)|"
    r"software\s+development\s+engineer\s+(iii|3|iv|4|v|5)"
    r")\b",
    re.IGNORECASE,
)


def _parse_posted_date(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%B %d, %Y")
    except Exception:
        return None


def _normalize_location(raw: str) -> List[str]:
    """
    Input:  Sunnyvale, California, USA
    Output: Sunnyvale, CA, US
    """
    if not raw:
        return []

    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        return [raw]

    city, state, country = parts

    state_map = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
        "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
        "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
        "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
        "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
        "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
        "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
        "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
        "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
        "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
        "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    }


    country_map = {
        "USA": "US",
        "United States": "US",
    }

    return [
        f"{city}, {state_map.get(state, state)}, {country_map.get(country, country)}"
    ]


def _fetch_page(offset: int, limit: int) -> Dict:
    """
    Use the SAME filters as browser:
    - Software Development
    - United States
    """
    params = {
        "offset": offset,
        "result_limit": limit,
        "sort": "recent",
        "category[]": "software-development",
        "country[]": "USA",
    }

    r = requests.get(AMAZON_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def scrape(max_pages: int = 10, page_size: int = 100) -> List[Dict]:
    """
    Returns normalized Amazon Software Development jobs (US only)
    """
    results: List[Dict] = []

    for page in range(max_pages):
        data = _fetch_page(page * page_size, page_size)
        jobs = data.get("jobs", [])
        if not jobs:
            break

        kept = 0

        for j in jobs:
            # 1️⃣ Enforce country
            if j.get("country_code") != "USA":
                continue

            # 2️⃣ Enforce software development category
            if j.get("job_category") != "Software Development":
                continue

            # 3️⃣ Reject senior / leadership roles
            title = j.get("title") or ""
            if REJECT_TITLE.search(title):
                continue

            external_id = str(j.get("id_icims") or j.get("id"))
            job_path = j.get("job_path") or ""

            results.append({
                "company": "Amazon",
                "external_job_id": external_id,
                "job_id": external_id,
                "title": title,
                "posting_url": (
                    f"https://www.amazon.jobs{job_path}"
                    if job_path.startswith("/")
                    else j.get("url")
                ),
                "posted_at": _parse_posted_date(j.get("posted_date")),
                "locations": _normalize_location(j.get("normalized_location")),
            })


            kept += 1

        print(
            f"Amazon page {page + 1}: "
            f"scanned={len(jobs)} kept={kept}"
        )

        time.sleep(0.4)

    # Deduplicate by external_job_id
    deduped = {j["external_job_id"]: j for j in results}
    print("Amazon jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    jobs = scrape(max_pages=5)
    print("Total Amazon jobs:", len(jobs))
    if jobs:
        print("Sample:", jobs[0])
