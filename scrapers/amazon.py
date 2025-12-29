import re
import json
import time
import requests
from datetime import datetime

AMAZON_SEARCH_URL = "https://www.amazon.jobs/en/search.json"

_KEEP_TITLE = re.compile(
    r"\b("
    r"software (development )?engineer\s*i\b|"
    r"software developer\s*i\b|"
    r"sde\s*i\b|sde\s*1\b|sde1\b|"
    r"sde\s*ii\b|sde\s*2\b|sde2\b|"
    r"new grad|new graduate|graduate|"
    r"entry level|junior|jr\.?\b"
    r")",
    re.IGNORECASE,
)

_REJECT_TITLE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|staff|lead|manager|architect|"
    r"\bii\b|\biii\b|\biv\b|\bv\b|"
    r"sde\s*(iii|iv)|"
    r"engineer\s*(ii|iii|iv)"
    r")\b",
    re.IGNORECASE,
)

_YEARS_RE = re.compile(r"(\d+)\s*\+\s*years", re.IGNORECASE)


def _parse_posted_date(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%B %d, %Y")
    except Exception:
        return None


def _looks_junior(job: dict) -> bool:
    title = (job.get("title") or "").strip()
    if not title:
        return False

    if not _KEEP_TITLE.search(title):
        return False

    if _REJECT_TITLE.search(title):
        return False

    bq = job.get("basic_qualifications") or ""
    m = _YEARS_RE.search(bq)
    if m and int(m.group(1)) >= 3:
        return False

    return True


def _fetch_page(offset: int, limit: int) -> dict:
    params = {
        "base_query": "software development engineer",
        "loc_query": "united states",
        "country": "USA",
        "offset": offset,
        "result_limit": limit,
        "sort": "relevant",
    }
    r = requests.get(AMAZON_SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _normalize_location(raw: str) -> list:
    if not raw:
        return []

    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        return [raw]

    city, state, country = parts
    state_map = {
        "California": "CA",
        "Washington": "WA",
        "Texas": "TX",
        "New York": "NY",
    }
    country_map = {
        "USA": "US",
        "United States": "US",
    }

    return [f"{city}, {state_map.get(state, state)}, {country_map.get(country, country)}"]


def scrape(max_pages: int = 50, page_size: int = 100) -> list[dict]:
    """
    Returns normalized Amazon jobs
    """
    results = []

    for page in range(max_pages):
        data = _fetch_page(page * page_size, page_size)
        jobs = data.get("jobs", [])
        if not jobs:
            break

        for j in jobs:
            if not _looks_junior(j):
                continue

            external_id = str(j.get("id_icims") or j.get("id"))
            job_path = j.get("job_path") or ""

            results.append({
                "company": "Amazon",
                "external_job_id": external_id,
                "job_id": external_id,
                "title": j.get("title"),
                "posting_url": (
                    f"https://www.amazon.jobs{job_path}"
                    if job_path.startswith("/")
                    else j.get("url")
                ),
                "posted_at": _parse_posted_date(j.get("posted_date")),
                "locations": _normalize_location(j.get("normalized_location")),
            })

        time.sleep(0.3)

    results.sort(key=lambda x: x.get("posted_at") or "", reverse=True)
    print("Amazon jobs:", len(results))
    return results


if __name__ == "__main__":
    jobs = scrape(max_pages=10)
