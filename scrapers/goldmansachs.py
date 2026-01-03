import re
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict

BASE_URL = "https://www.goldmansachs.com/careers/students/programs"
API_URL = "https://hdpc.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

REJECT_TITLE = re.compile(
    r"\b("
    r"director|principal|manager|head|lead|team\s*leader|"
    r"vice\s*president|president|squad\s*leader"
    r")\b",
    re.IGNORECASE,
)

ACCEPT_TITLE = re.compile(
    r"\b("
    r"software\s+engineer|software\s+developer|"
    r"software|engineer|developer"
    r")\b",
    re.IGNORECASE,
)

POSTED_DAYS_RE = re.compile(r"Posted\s+(\d+)\s+Days?\s+Ago", re.IGNORECASE)


def _parse_posted_at(posted_date: str):
    """Parse posted date from format like '2025-12-30'"""
    if not posted_date:
        return None
    
    try:
        # Parse ISO date format
        return datetime.strptime(posted_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _normalize_locations(primary_location: str) -> List[str]:
    if not primary_location:
        return []
    
    return [primary_location.strip()]


def scrape(max_pages: int = 20, page_size: int = 25) -> List[Dict]:
    jobs: List[Dict] = []
    offset = 0

    for page in range(max_pages):
        params = {
            "onlyData": "true",
            "expand": "requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields",
            "finder": f"findReqs;siteNumber=CX_3002,facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,limit={page_size},locationId=300000000229164,offset={offset},sortBy=POSTING_DATES_DESC"
        }

        try:
            r = requests.get(API_URL, params=params, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Goldman Sachs page {page + 1}: Request failed - {e}")
            break

        data = r.json()
        
        # Navigate to the requisition list
        items = data.get("items", [])
        if not items:
            break
        
        # Get the first item which contains the requisition list
        requisition_list = items[0].get("requisitionList", [])
        
        if not requisition_list:
            break

        kept = 0

        for job in requisition_list:
            title = job.get("Title") or ""
            
            # First check if title matches our accept filter
            if not ACCEPT_TITLE.search(title):
                continue
            
            # Then check if title matches reject filter
            if REJECT_TITLE.search(title):
                continue

            job_id = job.get("Id") or ""
            primary_location = job.get("PrimaryLocation", "")
            posted_date = job.get("PostedDate", "")
            
            # Construct job URL (Goldman Sachs uses Oracle Cloud format)
            job_url = f"https://www.goldmansachs.com/careers/find-a-role/role-detail.html?id={job_id}"

            jobs.append({
                "company": "Goldman Sachs",
                "external_job_id": job_id,
                "job_id": job_id,
                "title": title,
                "posting_url": job_url,
                "posted_at": _parse_posted_at(posted_date),
                "locations": _normalize_locations(primary_location),
            })

            kept += 1

        print(f"Goldman Sachs page {page + 1}: scanned={len(requisition_list)} kept={kept}")

        # Check if we got fewer results than requested, indicating last page
        if len(requisition_list) < page_size:
            break
        
        offset += page_size
        time.sleep(0.4)
    
    # Final dedupe by external_job_id
    deduped = {j["external_job_id"]: j for j in jobs}
    print("Goldman Sachs jobs:", len(deduped))

    return list(deduped.values())


if __name__ == "__main__":
    res = scrape(max_pages=10)
    print("Goldman Sachs jobs:", len(res))
    if res:
        print("Sample:", res[0])