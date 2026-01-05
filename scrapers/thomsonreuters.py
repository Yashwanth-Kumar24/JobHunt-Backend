import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://thomsonreuters.wd5.myworkdayjobs.com/en-US/External_Career_Site"
API_URL = "https://thomsonreuters.wd5.myworkdayjobs.com/wday/cxs/thomsonreuters/External_Career_Site/jobs"

# Reject leadership, non software, senior ownership roles
REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|lead|leader|head|architect|principal|staff|distinguished|"
    r"operations|service|support|analyst|tester|qa|president"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)


US_STATES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
    "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
    "minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire",
    "new jersey","new mexico","new york","north carolina","north dakota","ohio",
    "oklahoma","oregon","pennsylvania","rhode island","south carolina","south dakota",
    "tennessee","texas","utah","vermont","virginia","washington","west virginia",
    "wisconsin","wyoming","district of columbia"
}


def _parse_posted_at(posted_on: str):
    if not posted_on:
        return None

    now = datetime.now(timezone.utc)
    text = posted_on.strip().lower()

    if text == "posted today":
        return now

    if text == "posted yesterday":
        return now - timedelta(days=1)

    m = POSTED_DAYS_RE.search(posted_on)
    if m:
        return now - timedelta(days=int(m.group(1)))

    return None


def _is_us_job(states_text: str) -> bool:
    if not states_text:
        return False

    states = [s.strip().lower() for s in states_text.split(";")]
    return any(state in US_STATES for state in states)


def _normalize_locations(cities_text: str, states_text: str) -> List[str]:
    if not cities_text or not states_text:
        return []

    cities = [c.strip() for c in cities_text.split(";")]
    states = [s.strip() for s in states_text.split(";")]

    locations = []
    for i in range(min(len(cities), len(states))):
        locations.append(f"{cities[i]}, {states[i]}")

    return locations


def scrape(max_pages: int = 20, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "CF_Job_Posting_Anchor_Job_Category_EEB_Extended": [
                    "9276a62d4e68100204e60c54e1cc0001"
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
            print(f"Thomson Reuters page {page + 1}: request failed - {e}")
            break

        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0

        for job in postings:
            title = job.get("title") or ""
            bullet = job.get("bulletFields") or []

            if len(bullet) < 3:
                continue

            cities_text = bullet[0]
            states_text = bullet[1]
            external_job_id = bullet[2]

            # US-only filter
            if not _is_us_job(states_text):
                continue

            # Reject title filter
            if REJECT_TITLE.search(title):
                continue

            jobs.append({
                "company": "Thomson Reuters",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(cities_text, states_text),
            })

            kept += 1

        print(f"Thomson Reuters page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Thomson Reuters jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=15)
    print("Thomson Reuters jobs:", len(res))
    if res:
        print("Sample:", res[0])
    for x in res:
        print(x)