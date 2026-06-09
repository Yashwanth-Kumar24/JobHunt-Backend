import re
import time
import json
import base64
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

CAREERS_PAGE = "https://careers.snowflake.com/us/en/search-results"
API_URL = "https://careers.snowflake.com/widgets"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://careers.snowflake.com",
    "Referer": "https://careers.snowflake.com/us/en/search-results",
}

PAGE_SIZE = 10

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vice\s*president|president|architect|distinguished|fellow"
    r")\b",
    re.IGNORECASE,
)


def _get_csrf_token() -> tuple:
    """Fetch the careers page to get PLAY_SESSION cookie and extract CSRF token."""
    session = requests.Session()
    try:
        resp = session.get(CAREERS_PAGE, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=30)
        play_session = session.cookies.get("PLAY_SESSION")
        if play_session:
            # PLAY_SESSION is a JWT — decode the payload to get csrfToken
            try:
                payload_b64 = play_session.split(".")[1]
                # Add padding if needed
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                csrf_token = payload.get("data", {}).get("csrfToken")
                if csrf_token:
                    print(f"Snowflake session init: status={resp.status_code}, csrf=found")
                    return csrf_token, session
            except Exception:
                pass
        print(f"Snowflake session init: status={resp.status_code}, csrf=missing")
    except Exception as e:
        print(f"Snowflake session init failed: {e}")
    return None, session


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _normalize_locations(job: Dict) -> List[str]:
    multi = job.get("multi_location") or []
    if multi:
        return [loc.strip() for loc in multi if loc.strip()]
    loc = job.get("location") or ""
    return [loc.strip()] if loc.strip() else []


def scrape(max_pages: int = 10, page_size: int = PAGE_SIZE) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    csrf_token, session = _get_csrf_token()
    headers = dict(HEADERS)
    if csrf_token:
        headers["x-csrf-token"] = csrf_token

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    for page in range(max_pages):
        payload = {
            "lang": "en_us",
            "deviceType": "desktop",
            "country": "us",
            "pageName": "search-results",
            "ddoKey": "refineSearch",
            "from": offset,
            "size": page_size,
            "keywords": "",
            "jobs": True,
            "counts": True,
            "clearAll": False,
            "global": True,
            "siteType": "external",
            "jdsource": "facets",
            "sortBy": "Most recent",
            "sort": {"field": "postedDate", "order": "desc"},
            "selected_fields": {
                "category": ["Engineering"],
                "country": ["United States"],
            },
            "all_fields": ["category", "location", "type", "jobtypevalue"],
        }

        try:
            r = session.post(API_URL, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Snowflake page {page + 1}: request failed - {e}")
            break
        except ValueError:
            print(f"Snowflake page {page + 1}: invalid JSON response, skipping")
            break

        result = data.get("refineSearch", {})
        jobs_data = result.get("data", {}).get("jobs", [])
        total_hits = result.get("totalHits", 0)

        if not jobs_data:
            break

        kept = 0
        for job in jobs_data:
            job_id = job.get("jobId")
            title = (job.get("title") or "").strip()

            if not job_id or not title:
                continue

            if REJECT_TITLE.search(title):
                continue

            if job.get("country") != "United States":
                continue

            posted_at = _parse_posted_at(job.get("postedDate"))
            if not posted_at or posted_at < cutoff_date:
                continue

            apply_url = job.get("applyUrl") or f"https://careers.snowflake.com/us/en/job/{job_id}"

            jobs.append({
                "company": "Snowflake",
                "external_job_id": job_id,
                "job_id": job.get("reqId") or job_id,
                "title": title,
                "posting_url": apply_url,
                "posted_at": posted_at,
                "locations": _normalize_locations(job),
            })
            kept += 1

        print(f"Snowflake page {page + 1}: scanned={len(jobs_data)} kept={kept}")

        offset += page_size
        if offset >= total_hits:
            break

        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Snowflake jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("Snowflake jobs:", len(res))
    if res:
        print("Sample:", res[0])
