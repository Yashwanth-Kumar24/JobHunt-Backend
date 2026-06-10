import re
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict

# Remix data endpoint — works like a standard GET, returns JSON
API_URL = "https://job-boards.greenhouse.io/doordashusa"
DATA_PARAM = "routes/$url_token"

HEADERS = {
    "Accept": "application/json, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Referer": "https://job-boards.greenhouse.io/doordashusa",
}

# Exactly the two departments DoorDash uses on their own careers page filter
DEPT_IDS = [
    57486,   # 242 IT
    2438,    # 310 Engineering (parent — covers all engineering sub-departments)
]

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief"
    r")\b",
    re.IGNORECASE,
)

PAGE_SIZE = 50


def _parse_published_at(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).astimezone(timezone.utc)
    except Exception:
        return None


def scrape(max_pages: int = 10) -> List[Dict]:
    jobs: List[Dict] = []
    # No date cutoff — DoorDash's engineering board is small (2 pages) and roles stay open for months.
    # Capture all open positions; the frontend's range picker handles display filtering.

    # Build department query string manually (requests doesn't handle repeated keys well)
    dept_qs = "&".join(f"departments[]={d}" for d in DEPT_IDS)

    for page in range(1, max_pages + 1):
        url = f"{API_URL}?{dept_qs}&page={page}&_data={DATA_PARAM}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"DoorDash page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"DoorDash page {page}: invalid JSON")
            break

        posts = data.get("jobPosts", {})
        job_list = posts.get("data", [])
        total_pages = posts.get("total_pages", 1)

        if not job_list:
            break

        kept = 0
        for job in job_list:
            title = (job.get("title") or "").strip()
            if not title or REJECT_TITLE.search(title):
                continue

            loc_raw = job.get("location") or ""
            location_name = loc_raw.get("name") if isinstance(loc_raw, dict) else str(loc_raw)

            posted_at = _parse_published_at(job.get("published_at"))
            if not posted_at:
                continue

            job_id = str(job.get("id") or "")
            if not job_id:
                continue

            jobs.append({
                "company": "DoorDash",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": job.get("absolute_url") or f"https://job-boards.greenhouse.io/doordashusa/jobs/{job_id}",
                "posted_at": posted_at,
                "locations": [location_name] if location_name else [],
            })
            kept += 1

        print(f"DoorDash page {page}/{total_pages}: scanned={len(job_list)} kept={kept}")

        if page >= total_pages:
            break

        time.sleep(0.5)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("DoorDash jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total DoorDash jobs:", len(res))
    if res:
        print("Sample:", res[0])
