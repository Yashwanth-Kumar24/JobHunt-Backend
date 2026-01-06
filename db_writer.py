import psycopg2
import json
from psycopg2.extras import execute_values


def _get_company_ids(cur) -> dict:
    cur.execute("select id, name from companies;")
    return {name: cid for cid, name in cur.fetchall()}


def save_jobs(jobs, db_url, run_started_at):
    if not jobs:
        return {"inserted": 0, "new_jobs": []}

    with psycopg2.connect(
        db_url,
        sslmode="require",
        options="-c statement_timeout=10000",
    ) as conn:
        with conn.cursor() as cur:
            company_ids = _get_company_ids(cur)
            unique_rows = {}

            for j in jobs:
                company = j.get("company")
                if company not in company_ids:
                    raise RuntimeError(f"Company not found in DB: {company}")

                company_id = company_ids[company]
                external_job_id = str(j.get("external_job_id"))

                unique_rows[(company_id, external_job_id)] = (
                    company_id,
                    external_job_id,
                    j.get("job_id"),
                    j.get("title"),
                    j.get("posting_url"),
                    j.get("posted_at"),           # raw from API (may be NULL)
                    json.dumps(j.get("locations") or []),
                    run_started_at,               # first_seen_at
                    run_started_at,               # last_seen_at
                )

            rows = list(unique_rows.values())

            sql = """
            insert into jobs (
                company_id,
                external_job_id,
                job_id,
                title,
                posting_url,
                posted_at,
                locations,
                first_seen_at,
                last_seen_at
            )
            values %s
            on conflict (company_id, external_job_id)
            do update set
                job_id = excluded.job_id,
                title = excluded.title,
                posting_url = excluded.posting_url,
                locations = excluded.locations,
                last_seen_at = excluded.last_seen_at,
                -- ✅ update posted_at ONLY if DB is NULL AND API now provides value
                posted_at = CASE
                    WHEN jobs.posted_at IS NULL
                         AND excluded.posted_at IS NOT NULL
                    THEN excluded.posted_at
                    ELSE jobs.posted_at
                END;
            """

            # 🔑 This is where INSERT fallback happens
            execute_values(
                cur,
                sql,
                [
                    (
                        r[0],
                        r[1],
                        r[2],
                        r[3],
                        r[4],
                        r[5] if r[5] is not None else run_started_at,
                        r[6],
                        r[7],
                        r[8],
                    )
                    for r in rows
                ],
                page_size=200,
            )

            # Notifications: ONLY newly inserted rows
            cur.execute(
                """
                select
                    c.name,
                    j.title,
                    j.posting_url,
                    j.posted_at,
                    j.locations
                from jobs j
                join companies c on c.id = j.company_id
                where j.first_seen_at = %s
                order by j.first_seen_at asc;
                """,
                (run_started_at,),
            )

            new_jobs = []
            for r in cur.fetchall():
                loc = r[4]
                if isinstance(loc, str):
                    loc = json.loads(loc)
                elif loc is None:
                    loc = []
                elif not isinstance(loc, list):
                    loc = [str(loc)]

                new_jobs.append(
                    {
                        "company": r[0],
                        "title": r[1],
                        "posting_url": r[2],
                        "posted_at": r[3],
                        "locations": loc,
                    }
                )

            conn.commit()

            return {
                "inserted": len(new_jobs),
                "new_jobs": new_jobs,
            }
