import os

from scrapers.amazon import scrape as scrape_amazon
from scrapers.microsoft import scrape as scrape_microsoft
from scrapers.salesforce import scrape as scrape_salesforce
from scrapers.fidelity import scrape as scrape_fidelity
from scrapers.cognizant import scrape as scrape_cognizant
from scrapers.uwash import scrape as scrape_uwash
from db_writer import save_jobs

DB_URL = os.environ.get("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL not set")
    
jobs = []
jobs.extend(scrape_amazon(max_pages=10))
jobs.extend(scrape_microsoft(max_pages=10))
jobs.extend(scrape_salesforce(max_pages=2))
jobs.extend(scrape_fidelity(max_pages=2))
jobs.extend(scrape_cognizant(max_pages=5))
jobs.extend(scrape_uwash(max_pages=20))
print("Total Jobs found: ",len(jobs))
inserted = save_jobs(jobs, DB_URL)
print("Rows affected: ",inserted)