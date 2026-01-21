import re
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict

API_URL = (
    "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
    "recruitingCEJobRequisitions"
)

HEADERS = {
    "accept": "application/json",
    "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
    "origin": "https://careers.oracle.com",
    "referer": "https://careers.oracle.com/",
}

BASE_JOB_URL = "https://careers.oracle.com/en/sites/jobsearch/jobs/preview"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|vp|vice\s*president|"
    r"staff|senior\s+manager"
    r")\b",
    re.IGNORECASE,
)

def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        return None

def _is_us_job(primary: str, secondary: List[Dict]) -> bool:
    if primary and "United States" in primary:
        return True

    for loc in secondary or []:
        if loc.get("CountryCode") == "US":
            return True

    return False

def _normalize_locations(primary: str, secondary: List[Dict]) -> List[str]:
    locations = []

    if primary:
        locations.append(primary.strip())

    for loc in secondary or []:
        name = loc.get("Name")
        country = loc.get("CountryCode")
        if name and country:
            locations.append(f"{name}")

    return list(dict.fromkeys(locations))


def scrape(max_pages: int = 10, page_size: int = 14) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        params = {
            "onlyData": "true",
            "expand": (
                "requisitionList.workLocation,"
                "requisitionList.otherWorkLocations,"
                "requisitionList.secondaryLocations,"
                "requisitionList.requisitionFlexFields"
            ),
            "finder": (
                "findReqs;"
                "siteNumber=CX_45001,"
                "facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;"
                "TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,"
                f"limit={page_size},"
                f"offset={offset},"
                "sortBy=POSTING_DATES_DESC"
            ),
        }

        try:
            r = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Oracle page {page + 1}: request failed - {e}")
            break

        data = r.json()
        items = data.get("items", [])
        if not items:
            break

        requisitions = items[0].get("requisitionList", [])
        if not requisitions:
            break

        kept = 0

        for job in requisitions:
            job_id = job.get("Id")
            title = job.get("Title") or ""

            # Reject senior or leadership titles
            if REJECT_TITLE.search(title):
                continue

            primary_loc = job.get("PrimaryLocation")
            secondary_locs = job.get("secondaryLocations")

            # Reject non US jobs
            if not _is_us_job(primary_loc, secondary_locs):
                continue


            jobs.append({
                "company": "Oracle",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": f"{BASE_JOB_URL}/{job_id}",
                "posted_at": _parse_posted_at(job.get("PostedDate")),
                "locations": _normalize_locations(
                    primary_loc,
                    secondary_locs
                ),
            })

            kept += 1

        print(
            f"Oracle page {page + 1}: scanned={len(requisitions)} kept={kept}"
        )

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Oracle jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=1)
    print("Oracle jobs:", len(res))
    if res:
        print("Sample:", res[0])
