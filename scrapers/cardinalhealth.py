import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://cardinalhealth.wd1.myworkdayjobs.com/en-US/EXT"
API_URL = "https://cardinalhealth.wd1.myworkdayjobs.com/wday/cxs/cardinalhealth/EXT/jobs"
CAREERS_PAGE = "https://cardinalhealth.wd1.myworkdayjobs.com/en-US/EXT"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://cardinalhealth.wd1.myworkdayjobs.com",
    "Referer": CAREERS_PAGE,
}

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|vp|vice\s*president|president|"
    r"staff|distinguished|architect|advisor|consultant|fellow"
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


def _normalize_locations(loc_text: str) -> List[str]:
    if not loc_text:
        return []
    # Format: "OH-Ohio-FIELD", "OH-Dublin-Cardinal Place", "US-Nationwide-FIELD"
    parts = loc_text.split("-", 2)
    if len(parts) == 3:
        state_abbr, state_name, city_or_type = parts
        city_or_type = city_or_type.strip()
        if city_or_type.upper() in ("FIELD", "WORK FROM HOME"):
            return [f"{state_name.strip()}, {state_abbr.strip()}, US"]
        return [f"{city_or_type}, {state_abbr.strip()}, US"]
    return [loc_text.strip()]


def _get_session_headers():
    session = requests.Session()
    try:
        resp = session.get(CAREERS_PAGE, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=30)
        csrf_token = session.cookies.get("CALYPSO_CSRF_TOKEN")
        print(f"Cardinal Health session init: status={resp.status_code}, csrf={'found' if csrf_token else 'missing'}")
        h = dict(HEADERS)
        if csrf_token:
            h["x-calypso-csrf-token"] = csrf_token
        return h, session
    except Exception as e:
        print(f"Cardinal Health session init failed: {e}")
    return HEADERS, requests.Session()


def scrape(max_pages: int = 10, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    headers, session = _get_session_headers()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "Location_Country": ["bc33aa3152ec42d4995f4791a106ed09"],
                "jobFamilyGroup": [
                    "d60818d48fb20100f9947f752b3d0000",
                    "18e1778e3dfc455b8d4ba4566ded3c06",
                ],
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = session.post(API_URL, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Cardinal Health page {page + 1}: request failed - {e}")
            break
        except ValueError:
            print(f"Cardinal Health page {page + 1}: invalid JSON response, skipping")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0
        for job in postings:
            title = (job.get("title") or "").strip()
            if not title or REJECT_TITLE.search(title):
                continue

            posted_at = _parse_posted_at(job.get("postedOn"))
            if not posted_at or posted_at < cutoff_date:
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = (
                bullet[0] if bullet
                else job.get("externalPath", "").split("/")[-1]
            )
            if not external_job_id:
                continue

            jobs.append({
                "company": "Cardinal Health",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": posted_at,
                "locations": _normalize_locations(job.get("locationsText")),
            })
            kept += 1

        print(f"Cardinal Health page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Cardinal Health jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Cardinal Health jobs:", len(res))
    if res:
        print("Sample:", res[0])
