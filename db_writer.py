import psycopg2
import json
from psycopg2.extras import execute_values
from typing import List, Dict


def _get_company_ids(cur) -> dict:
    cur.execute("select id, name from companies;")
    return {name: cid for cid, name in cur.fetchall()}


def save_jobs(
    jobs: List[Dict],
    db_url: str,
    update_last_seen: bool = True,
) -> int:
    if not jobs:
        return 0

    with psycopg2.connect(
        db_url,
        sslmode="require",
        options="-c statement_timeout=10000",
    ) as conn:
        with conn.cursor() as cur:
            company_ids = _get_company_ids(cur)

            # --------------------------------------------------
            # Deduplicate rows by (company_id, external_job_id)
            # --------------------------------------------------
            unique_rows = {}

            for j in jobs:
                company = j.get("company")
                if company not in company_ids:
                    raise RuntimeError(f"Company not found in DB: {company}")

                company_id = company_ids[company]
                external_job_id = str(j.get("external_job_id"))

                key = (company_id, external_job_id)

                # Last write wins (latest scrape data preserved)
                unique_rows[key] = (
                    company_id,
                    external_job_id,
                    j.get("job_id"),
                    j.get("title"),
                    j.get("posting_url"),
                    j.get("posted_at"),
                    json.dumps(j.get("locations") or []),
                )

            rows = list(unique_rows.values())

            if not rows:
                return 0

            print(f"DB Writer: deduped {len(jobs)} → {len(rows)} rows")

            # --------------------------------------------------
            # Upsert SQL
            # --------------------------------------------------
            if update_last_seen:
                sql = """
                insert into jobs (
                    company_id,
                    external_job_id,
                    job_id,
                    title,
                    posting_url,
                    posted_at,
                    locations
                )
                values %s
                on conflict (company_id, external_job_id)
                do update set
                    job_id = excluded.job_id,
                    title = excluded.title,
                    posting_url = excluded.posting_url,
                    posted_at = excluded.posted_at,
                    locations = excluded.locations,
                    last_seen_at = now();
                """
            else:
                sql = """
                insert into jobs (
                    company_id,
                    external_job_id,
                    job_id,
                    title,
                    posting_url,
                    posted_at,
                    locations
                )
                values %s
                on conflict (company_id, external_job_id)
                do update set
                    job_id = excluded.job_id,
                    title = excluded.title,
                    posting_url = excluded.posting_url,
                    posted_at = excluded.posted_at,
                    locations = excluded.locations;
                """

            execute_values(cur, sql, rows, page_size=200)
            conn.commit()

            return cur.rowcount
