import time
import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict

BASE_URL = "https://snapchat.wd1.myworkdayjobs.com/snap"
API_URL = "https://snapchat.wd1.myworkdayjobs.com/wday/cxs/snapchat/snap/jobs"

# Reject senior / leadership / non IC roles
REJECT_TITLE = re.compile(
    r"\b("
    r"principal|staff|director|manager|head|lead|vp|vice\s*president|spectacles|"
    r"senior\s+manager|pcb|npi|senior\s+director|staff|optical|embedded|electrical|hardware|process"
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


def scrape(max_pages: int = 15, page_size: int = 20) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    SNAP_LOCATIONS = [
        "95d6b3b2e7d91001614ca11093850000",
        "fad1b9bbc305019817878678061de155",
        "1763d6f1e9be0121f90261be5b4d856e",
        "efe1a865073101e5380680f9020a7437",
        "efe1a865073101b9db6c8da7020a6037",
        "256f279d5e741082c567c24fca236272",
        "a47fe10a5e6210b95624c5690b522fe0",
        "efe1a865073101ddec60ef19020afc36",
        "137dd6cbab601000bf830bdee83d0000",
        "d6bc0f25c18601ac60ecf0a80d02124d",
        "b6d8d8a3809d10016c27d22429420000",
        "c52c83bb81a21000cf303bd607c00000",
        "efe1a86507310105e56ad10d020af736",
        "efe1a8650731016c130aaddd010aed36",
        "b9cf6982655e1001a9ff7ae350d10000",
        "7a68e5b6d6b51001a9de39167c5f0000",
        "16f9d2b5501e1001b601bc0872be0000",
        "8bf70c1877bb01f58a864a033aab9149",
        "efe1a86507310187e01ef207030a7937",
        "2b0a835c9646011d58da08236e4f6726",
    ]


    for page in range(max_pages):
        payload = {
            "appliedFacets": {
                "jobFamily": [
                    "8d73f0a7971d102b9db74b4c3651e667",
                    "8d73f0a7971d102b9d459841e16ae3a5",
                    "80a3a1160116015e0d6b64caaa14b598",
                ],
                "locations": SNAP_LOCATIONS,
            },
            "limit": page_size,
            "offset": offset,
            "searchText": "",
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Snap Inc page {page + 1}: request failed - {e}")
            break

        data = r.json()
        
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
                "company": "Snap Inc.",
                "external_job_id": external_job_id,
                "job_id": external_job_id,
                "title": title,
                "posting_url": BASE_URL + job.get("externalPath", ""),
                "posted_at": _parse_posted_at(job.get("postedOn")),
                "locations": _normalize_locations(job.get("locationsText")),
            })

            kept += 1

        print(f"Snap Inc page {page + 1}: scanned={len(postings)} kept={kept}")

        offset += page_size
        time.sleep(0.4)

    deduped = {j["external_job_id"]: j for j in jobs}
    print("Snap Inc jobs:", len(deduped))
    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=3)
    print("Snap Inc jobs:", len(res))
    if res:
        print("Sample:", res[0])
