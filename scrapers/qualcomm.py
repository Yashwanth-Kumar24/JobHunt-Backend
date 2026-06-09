import re
import time
import requests
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict

BASE = "https://careers.qualcomm.com"
SEARCH = f"{BASE}/api/pcsx/search"
CAREERS_PAGE = f"{BASE}/careers"

# Software-focused job families only
JOB_FAMILIES = [
    "software engineering",
    "software applications engineering",
    "it engineering",
    "it software developer",
    "it data engineer",
    "systems engineering",
    "machine learning engineering",
    "cyber security engineering",
    "graphics software engineering",
    "data science",
]

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"clearance|secret|gov|qgov"
    r")\b",
    re.IGNORECASE,
)


def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": CAREERS_PAGE,
    })
    return s


def _get_csrf_token(session: requests.Session) -> str | None:
    """Fetch careers page to get x-csrf-token from response headers."""
    try:
        resp = session.get(CAREERS_PAGE, headers={"Accept": "text/html"}, timeout=30)
        token = resp.headers.get("x-csrf-token")
        print(f"Qualcomm session init: status={resp.status_code}, csrf={'found' if token else 'missing'}")
        return token
    except Exception as e:
        print(f"Qualcomm session init failed: {e}")
        return None


def _to_posted_at(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _keep_title(title: str) -> bool:
    if not title:
        return False
    # Qualcomm often has "— Engineer, Senior" suffix or "#Title" prefix
    title = title.lstrip("#").strip()
    return not REJECT_TITLE.search(title)


def scrape(max_pages: int = 20) -> List[Dict]:
    session = _session()
    csrf_token = _get_csrf_token(session)
    if csrf_token:
        session.headers["x-csrf-token"] = csrf_token

    start = 0
    results = []

    for page in range(max_pages):
        params = {
            "domain": "qualcomm.com",
            "query": "",
            "location": "United States",
            "start": start,
            "sort_by": "distance",
        }
        # Add each job family as a separate param
        for jf in JOB_FAMILIES:
            params.setdefault("filter_job_family", [])
            if isinstance(params["filter_job_family"], list):
                params["filter_job_family"].append(jf)

        try:
            r = session.get(SEARCH, params=params, timeout=(5, 20))
            r.raise_for_status()
            positions = r.json().get("data", {}).get("positions", [])
        except requests.RequestException as e:
            print(f"Qualcomm page {page + 1}: request failed - {e}")
            break
        except ValueError:
            print(f"Qualcomm page {page + 1}: invalid JSON response, skipping")
            break

        if not positions:
            break

        kept = 0
        for p in positions:
            title = (p.get("name") or "").strip()
            if not _keep_title(title):
                continue

            # US only — standardizedLocations always has ", US" suffix
            locs = p.get("standardizedLocations") or p.get("locations") or []
            us_locs = [l for l in locs if ", US" in l or "United States" in l]
            if not us_locs:
                continue

            pos_url = p.get("positionUrl") or ""

            results.append({
                "company": "Qualcomm",
                "external_job_id": str(p.get("id")),
                "job_id": p.get("displayJobId") or str(p.get("id")),
                "title": title.lstrip("#").strip(),
                "posting_url": BASE + pos_url if pos_url.startswith("/") else pos_url,
                "posted_at": _to_posted_at(p.get("postedTs")),
                "locations": us_locs,
            })
            kept += 1

        print(f"Qualcomm page {page + 1}: scanned={len(positions)} kept={kept}")

        start += len(positions)
        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in results}
    print("Qualcomm jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    jobs = scrape(max_pages=5)
    print("Total Qualcomm jobs:", len(jobs))
    if jobs:
        print("Sample:", jobs[0])
