import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers"
API_URL = "https://cisco.wd5.myworkdayjobs.com/wday/cxs/cisco/Cisco_Careers/jobs"

# Reject leadership, non software, hardware focused roles
REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|lead|leader|architect|principal|staff|distinguished|"
    r"hardware|thermal|silicon|fpga|asic|power|electrical|mechanical|post[-\s]?silicon|"
    r"validation|design|modeling|photonic|optical|marketing|advisor|cad|embedded|integration"
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

    # Covers:
    # "San Jose, California, US"
    # "2 Locations"
    # "3 Locations"
    # "United States"
    if "us" in text or "united states" in text or "locations" in text:
        return True

    return False


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []
    # "2 Locations" / "3 Locations" are placeholder strings, not real locations
    if re.match(r"^\d+\s+locations?$", loc_text.strip(), re.IGNORECASE):
        return []
    return [loc_text.strip()]


def scrape(max_pages: int = 20, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "jobFamilyGroup": [
                    "2101eee3ea96016aef42a674fc016429",
                    "2101eee3ea96017b1ceba674fc016829",
                ]
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Cisco page {page + 1}: request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""
            locations_text = job.get("locationsText") or ""

            # US location check
            if not _is_us_location(locations_text):
                continue

            # Reject unwanted titles
            if REJECT_TITLE.search(title):
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = (
                bullet[0]
                if bullet
                else job.get("externalPath", "").split("/")[-1]
            )

            jobs.append({
                "company": "Cisco",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(locations_text),
            })

            kept += 1

        print(f"Cisco page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Cisco jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=15)
    print("Cisco jobs:", len(res))
    if res:
        print("Sample:", res[0])
    for x in res:
        print(x)
