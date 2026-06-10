import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://guidewire.wd5.myworkdayjobs.com/external"
API_URL  = "https://guidewire.wd5.myworkdayjobs.com/wday/cxs/guidewire/external/jobs"

# US location IDs (from Guidewire careers page filter)
US_LOCATION_IDS = [
    "1921b797f51c1000b4adc3e7982b0000",
    "1921b797f51c1000b4aec47bd6c10000",
    "74c90e9c7b4310806e7d34dc093f57f3",
    "d8852b6046301000b4ae7d59063e0000",
]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
}

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief|consultant|executive"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE    = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago",  re.IGNORECASE)
POSTED_30PLUS_RE  = re.compile(r"Posted\s+30\+\s+Days?\s+Ago",   re.IGNORECASE)


def _parse_posted_at(posted_on: str):
    if not posted_on:
        return None
    now = datetime.now(timezone.utc)
    text = posted_on.strip().lower()
    if text == "posted today":
        return now
    if text == "posted yesterday":
        return now - timedelta(days=1)
    if POSTED_30PLUS_RE.search(posted_on):
        return now - timedelta(days=31)
    m = POSTED_DAYS_RE.search(posted_on)
    if m:
        return now - timedelta(days=int(m.group(1)))
    return None


def _normalize_location(loc_text: str) -> str:
    if not loc_text:
        return ""
    # "United States - San Mateo, CA" → "San Mateo, CA"
    if " - " in loc_text:
        return loc_text.split(" - ", 1)[-1].strip()
    return loc_text.strip()


def scrape(max_pages: int = 5, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    offset = 0

    for page in range(1, max_pages + 1):
        payload = {
            "appliedFacets": {"locations": US_LOCATION_IDS},
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Guidewire page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"Guidewire page {page}: invalid JSON")
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
            if not posted_at or posted_at < cutoff:
                continue

            bullet = job.get("bulletFields") or []
            job_id = bullet[0] if bullet else ""
            if not job_id:
                continue

            loc_text = job.get("locationsText") or ""
            loc = _normalize_location(loc_text)

            jobs.append({
                "company": "Guidewire",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": BASE_URL + (job.get("externalPath") or ""),
                "posted_at": posted_at,
                "locations": [loc] if loc else [],
            })
            kept += 1

        print(f"Guidewire page {page}: scanned={len(postings)} kept={kept}")

        if offset + page_size >= data.get("total", 0):
            break

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Guidewire jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total Guidewire jobs:", len(res))
    if res:
        for j in res[:5]:
            print(f"  {j['title']} | {j['locations']} | {j['posted_at'].date()}")
