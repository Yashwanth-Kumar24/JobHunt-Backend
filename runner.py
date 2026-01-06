import os
from datetime import datetime, timezone

from scrapers.amazon import scrape as scrape_amazon
from scrapers.microsoft import scrape as scrape_microsoft
from scrapers.salesforce import scrape as scrape_salesforce
from scrapers.fidelity import scrape as scrape_fidelity
from scrapers.cognizant import scrape as scrape_cognizant
from scrapers.uwash import scrape as scrape_uwash
from scrapers.doordash import scrape as scrape_doordash
from scrapers.ssc import scrape as scrape_ssc
from scrapers.synechron import scrape as scrape_synechron
from scrapers.goldmansachs import scrape as scrape_goldmansachs
from scrapers.pennstate import scrape as scrape_pennstate
from scrapers.geico import scrape as scrape_geico
from scrapers.cisco import scrape as scrape_cisco
from scrapers.thomsonreuters import scrape as scrape_thomsonreuters
from scrapers.susquehanna import scrape as scrape_susquehanna
from db_writer import save_jobs

DB_URL = os.environ.get("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL not set")

run_started_at = datetime.now(timezone.utc)
jobs = []
jobs.extend(scrape_amazon(max_pages=5))
jobs.extend(scrape_microsoft(max_pages=5))
jobs.extend(scrape_salesforce(max_pages=5))
jobs.extend(scrape_fidelity(max_pages=5))
jobs.extend(scrape_cognizant(max_pages=5))
jobs.extend(scrape_uwash(max_pages=5))
jobs.extend(scrape_doordash(max_pages=1))
jobs.extend(scrape_ssc(max_pages=3))
jobs.extend(scrape_synechron(max_pages=2))
jobs.extend(scrape_goldmansachs(max_pages=5))
jobs.extend(scrape_pennstate(max_pages=5))
jobs.extend(scrape_geico(max_pages=5))
jobs.extend(scrape_cisco(max_pages=5))
jobs.extend(scrape_thomsonreuters(max_pages=5))
jobs.extend(scrape_susquehanna(max_pages=5))
print("Total Jobs found: ",len(jobs))
result = save_jobs(jobs, DB_URL, run_started_at)
print("New jobs added:", result["inserted"])
if result["inserted"] > 0:
    notify_telegram(result["new_jobs"])