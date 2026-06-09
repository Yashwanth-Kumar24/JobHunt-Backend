import re
import time
import base64
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

CAREERS_PAGE = "https://jobs.cincinnatichildrens.org/search-jobs"
API_URL = "https://jobs.cincinnatichildrens.org/widgets"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://jobs.cincinnatichildrens.org",
    "Referer": CAREERS_PAGE,
}

REJECT_TITLE = re.compile(
    r"\b("
    r"director|manager|head|vp|vice\s*president|president|"
    r"architect|principal|distinguished|fellow|chief|advisor"
    r")\b",
    re.IGNORECASE,
)


def _get_csrf_token() -> tuple:
    """Fetch careers page, extract PLAY_SESSION JWT and decode csrfToken."""
    session = requests.Session()
    try:
        resp = session.get(CAREERS_PAGE, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=30)
        play_session = session.cookies.get("PLAY_SESSION")
        if play_session:
            try:
                payload_b64 = play_session.split(".")[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.b64decode(payload_b64))
                csrf = payload.get("data", {}).get("csrfToken")
                if csrf:
                    print(f"Cincinnati Children's session init: status={resp.status_code}, csrf=found")
                    return csrf, session
            except Exception:
                pass
        print(f"Cincinnati Children's session init: status={resp.status_code}, csrf=missing")
    except Exception as e:
        print(f"Cincinnati Children's session init failed: {e}")
    return None, session


def _parse_posted_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("+0000", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def scrape(max_pages: int = 10, page_size: int = 10) -> List[Dict]:
    jobs: List[Dict] = []
    csrf_token, session = _get_csrf_token()
    if not csrf_token:
        print("Cincinnati Children's: no CSRF token, skipping")
        return []

    headers = dict(HEADERS)
    headers["x-csrf-token"] = csrf_token

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    offset = 0

    for page in range(max_pages):
        payload = {
            "lang": "en_us",
            "deviceType": "desktop",
            "country": "us",
            "pageName": "search-results",
            "ddoKey": "refineSearch",
            "pageId": "page23-ds",
            "selected_fields": {"category": ["Information Services"]},
            "sort": {"order": "desc", "field": "postedDate"},
            "sortBy": "Most recent",
            "from": offset,
            "size": page_size,
            "global": True,
            "irs": False,
            "isSliderEnable": False,
            "jobs": True,
            "counts": True,
            "clearAll": False,
            "keywords": "",
            "siteType": "external",
            "jdsource": "facets",
            "subsearch": "",
            "all_fields": ["category", "department", "WorkLocation", "type", "shift"],
            "locationData": {},
        }

        try:
            r = session.post(API_URL, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Cincinnati Children's page {page + 1}: request failed - {e}")
            break
        except ValueError:
            print(f"Cincinnati Children's page {page + 1}: invalid JSON, skipping")
            break

        raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
        if not raw_jobs:
            break

        kept = 0
        stop_early = False

        for job in raw_jobs:
            title = (job.get("title") or "").strip()
            if not title or REJECT_TITLE.search(title):
                continue

            posted_at = _parse_posted_at(job.get("postedDate"))
            if not posted_at or posted_at < cutoff:
                stop_early = True
                break

            job_id = str(job.get("jobId") or job.get("reqId") or "")
            if not job_id:
                continue

            # Build direct job URL from applyUrl by stripping /apply
            apply_url = job.get("applyUrl") or ""
            posting_url = apply_url.rsplit("/apply", 1)[0] if "/apply" in apply_url else apply_url

            location = (job.get("location") or "").strip()

            jobs.append({
                "company": "Cincinnati Children's",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": posting_url,
                "posted_at": posted_at,
                "locations": [location] if location else [],
            })
            kept += 1

        print(f"Cincinnati Children's page {page + 1}: scanned={len(raw_jobs)} kept={kept}")

        if stop_early or len(raw_jobs) < page_size:
            break

        offset += page_size
        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Cincinnati Children's jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=5)
    print("Total:", len(res))
    if res:
        print("Sample:", res[0])
