import re
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://cvshealth.wd1.myworkdayjobs.com/en-US/CVS_Health_Careers"
API_URL  = "https://cvshealth.wd1.myworkdayjobs.com/wday/cxs/cvshealth/CVS_Health_Careers/jobs"

# Technology / DDAT job family group ID (from careers page filter)
TECH_JOB_FAMILY = "e65dbadf6a50100168ed86fe4cf50001"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
}

REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|director|manager|head|lead|"
    r"vp|vice\s*president|president|architect|distinguished|fellow|"
    r"partner|advisor|counsel|recruiter|chief|executive|field\s+service"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE   = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)
POSTED_30PLUS_RE = re.compile(r"Posted\s+30\+\s+Days?\s+Ago",  re.IGNORECASE)


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
    # "TX - Work from home" → "Work from home, TX"
    # "Work At Home-Connecticut" → keep as-is
    # "49 Locations" → keep as-is
    if " - " in loc_text:
        state, city = loc_text.split(" - ", 1)
        return f"{city.strip()}, {state.strip()}"
    return loc_text.strip()


def scrape(max_pages: int = 15, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    offset = 0

    for page in range(1, max_pages + 1):
        payload = {
            "appliedFacets": {"jobFamilyGroup": [TECH_JOB_FAMILY]},
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"CVS Health page {page}: request failed - {e}")
            break
        except ValueError:
            print(f"CVS Health page {page}: invalid JSON")
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

            external_path = job.get("externalPath") or ""
            loc = _normalize_location(job.get("locationsText") or "")

            jobs.append({
                "company": "CVS Health",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": BASE_URL + external_path,
                "posted_at": posted_at,
                "locations": [loc] if loc else [],
            })
            kept += 1

        print(f"CVS Health page {page}: scanned={len(postings)} kept={kept}")

        if offset + page_size >= data.get("total", 0):
            break

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("CVS Health jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape()
    print("Total CVS Health jobs:", len(res))
    if res:
        for j in res[:5]:
            print(f"  {j['title']} | {j['locations']} | {j['posting_url']}")
