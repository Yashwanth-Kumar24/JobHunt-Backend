import time
import re
import requests
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://apply.careers.microsoft.com"
SEARCH = f"{BASE}/api/pcsx/search"

_REJECT_TITLE = re.compile(
    r"\b("
    r"principal|staff|senior|sr\.?|lead|manager|director|head|vp|architect|ctj|poly|secret|"
    r"distinguished|fellow|ic4|"
    r"sde\s*(3|iii|4|iv)|"
    r"software engineer\s*(iii|3|iv|4|v|5)"
    r")\b",
    re.IGNORECASE,
)

_ALLOW_PREFIX = re.compile(r"\bsoftware engineer\b", re.IGNORECASE)


def _session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 JobTracker/1.0",
        "Accept": "application/json",
        "Referer": f"{BASE}/careers",
        "Origin": BASE,
    })
    return s


def _keep_title(title: str) -> bool:
    if not title:
        return False
    t = " ".join(title.strip().split())
    return bool(_ALLOW_PREFIX.search(t) and not _REJECT_TITLE.search(t))


def _to_posted_at(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def scrape(max_pages: int = 20) -> list[dict]:
    """
    Returns normalized Microsoft jobs
    """
    s = _session()
    start = 0
    results = []

    for page in range(max_pages):
        params = {
            "domain": "microsoft.com",
            "hl": "en",
            "query": "software engineer",
            "location": "United States",
            "sort_by": "timestamp",
            "start": start,
        }

        r = s.get(SEARCH, params=params, timeout=(5, 15))
        r.raise_for_status()

        positions = r.json().get("data", {}).get("positions", [])
        if not positions:
            break

        for p in positions:
            title = p.get("name") or ""
            if not _keep_title(title):
                continue

            pos_url = p.get("positionUrl") or ""

            results.append({
                "company": "Microsoft",
                "external_job_id": str(p.get("id")),
                "job_id": p.get("displayJobId"),
                "title": title,
                "posting_url": (
                    BASE + pos_url if pos_url.startswith("/") else pos_url
                ),
                "posted_at": _to_posted_at(p.get("postedTs")),
                "locations": p.get("standardizedLocations")
                    or p.get("locations")
                    or [],
            })

        start += len(positions)
        time.sleep(0.5)
    print("Microsoft jobs:", len(results))
    return results


if __name__ == "__main__":
    jobs = scrape(max_pages=5)
