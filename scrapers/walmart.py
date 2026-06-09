import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal"
API_URL = "https://walmart.wd504.myworkdayjobs.com/wday/cxs/walmart/WalmartExternal/jobs"
CAREERS_PAGE = "https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://walmart.wd504.myworkdayjobs.com",
    "Referer": "https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal",
}

# Reject senior / leadership / non IC roles
REJECT_TITLE = re.compile(
    r"\b("
    r"principal|staff|director|manager|head|lead|vp|vice\s*president|spectacles|"
    r"senior\s+manager|pcb|npi|senior\s+director|distinguished|architect"
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
    return [loc_text.strip()]


def _get_session_headers():
    """Visit the careers page to obtain CSRF token cookie, then return headers with it."""
    session = requests.Session()
    try:
        resp = session.get(CAREERS_PAGE, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=30)
        csrf_token = session.cookies.get("CALYPSO_CSRF_TOKEN")
        print(f"Walmart session init: status={resp.status_code}, csrf={'found' if csrf_token else 'missing'}")
        h = dict(HEADERS)
        if csrf_token:
            h["x-calypso-csrf-token"] = csrf_token
        return h, session
    except Exception as e:
        print(f"Walmart session init failed: {e}")
    return HEADERS, session


def scrape(max_pages: int = 15, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    headers, session = _get_session_headers()

    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "jobFamilyGroup": [
                    "e83ebdbd2a0a01e7e1477a8948e904c6",
                    "e83ebdbd2a0a01af0185848948e94dc6"
                ],
                "locationCountry": ["bc33aa3152ec42d4995f4791a106ed09"],
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
            print(f"Walmart page {page + 1}: request failed - {e}")
            break
        except ValueError:
            print(f"Walmart page {page + 1}: invalid JSON response (status={r.status_code}), skipping")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break

        kept = 0
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        for job in postings:
            title = job.get("title") or ""

            posted_at = _parse_posted_at(job.get("postedOn"))

            # Reject unwanted roles
            if REJECT_TITLE.search(title):
                continue

            # Drop jobs older than 30 days or unknown dates
            if not posted_at or posted_at < cutoff_date:
                continue

            bullet = job.get("bulletFields") or []
            external_job_id = (
                bullet[0]
                if bullet
                else job.get("externalPath", "").split("/")[-1]
            )

            jobs.append({
                "company": "Walmart",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": posted_at,
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"Walmart page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Walmart jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Walmart jobs:", len(res))
    if res:
        print("Sample:", res[0])
