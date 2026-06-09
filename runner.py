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
from scrapers.snapinc import scrape as scrape_snapinc
from scrapers.apple import scrape as scrape_apple
from scrapers.walmart import scrape as scrape_walmart
from scrapers.lilly import scrape as scrape_lilly
from scrapers.nvidia import scrape as scrape_nvidia
from scrapers.visa import scrape as scrape_visa
from scrapers.oracle import scrape as scrape_oracle
from scrapers.snowflake import scrape as scrape_snowflake
from scrapers.uber import scrape as scrape_uber
from scrapers.cardinalhealth import scrape as scrape_cardinalhealth
from scrapers.greenhouse import scrape as scrape_greenhouse
from scrapers.qualcomm import scrape as scrape_qualcomm
from scrapers.amd import scrape as scrape_amd
from scrapers.cincinnatichildrens import scrape as scrape_cincinnati
from scrapers.wayfair import scrape as scrape_wayfair
from scrapers.elevancehealth import scrape as scrape_elevancehealth

from db_writer import save_jobs
from notify_telegram import notify_telegram


DB_URL = os.environ.get("SUPABASE_DB_URL")
if not DB_URL:
    raise RuntimeError("SUPABASE_DB_URL not set")

run_started_at = datetime.now(timezone.utc)

jobs = []
jobs.extend(scrape_amazon(max_pages=5))
jobs.extend(scrape_microsoft(max_pages=10))
jobs.extend(scrape_salesforce(max_pages=5))
jobs.extend(scrape_fidelity(max_pages=5))
jobs.extend(scrape_cognizant(max_pages=5))
jobs.extend(scrape_uwash(max_pages=5))
# jobs.extend(scrape_doordash(max_pages=1))
jobs.extend(scrape_ssc(max_pages=5))
jobs.extend(scrape_synechron(max_pages=2))
jobs.extend(scrape_goldmansachs(max_pages=5))
jobs.extend(scrape_pennstate(max_pages=5))
jobs.extend(scrape_geico(max_pages=5))
jobs.extend(scrape_cisco(max_pages=5))
jobs.extend(scrape_thomsonreuters(max_pages=5))
jobs.extend(scrape_susquehanna(max_pages=5))
jobs.extend(scrape_snapinc(max_pages=5))
jobs.extend(scrape_apple(max_pages=5))
jobs.extend(scrape_walmart(max_pages=5))
jobs.extend(scrape_lilly(max_pages=5))
jobs.extend(scrape_nvidia(max_pages=5))
jobs.extend(scrape_visa())
jobs.extend(scrape_oracle(max_pages=12))
jobs.extend(scrape_snowflake(max_pages=10))
jobs.extend(scrape_uber(max_pages=15))
jobs.extend(scrape_cardinalhealth(max_pages=10))
jobs.extend(scrape_greenhouse())
jobs.extend(scrape_qualcomm(max_pages=20))
jobs.extend(scrape_amd(max_pages=20))
jobs.extend(scrape_cincinnati(max_pages=10))
jobs.extend(scrape_wayfair())
jobs.extend(scrape_elevancehealth(max_pages=10))

print("Total jobs scraped:", len(jobs))

result = save_jobs(jobs, DB_URL, run_started_at)

print("New jobs added:", result["inserted"])

if result["inserted"] > 0:
    notify_telegram(result["new_jobs"])
