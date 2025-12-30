import os

from scrapers.amazon import scrape as scrape_amazon
from scrapers.microsoft import scrape as scrape_microsoft
from db_writer import save_jobs

DB_URL = os.environ.get("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL not set")
    
jobs = []
jobs.extend(scrape_amazon())
jobs.extend(scrape_microsoft())
print("Total Jobs found: ",len(jobs))
inserted = save_jobs(jobs, DB_URL)
print("Rows affected: ",inserted)