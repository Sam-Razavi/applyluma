"""Compact bloated Postgres tables and (optionally) lower memory settings.

Why: job retention archives and slims tens of thousands of postings a night.
Postgres keeps the dead row versions on disk, and plain autovacuum only marks
that space reusable; it never hands it back. The files stay large, so Postgres
caches more pages than the live data needs, and Railway bills that memory.

This script NEVER deletes or edits rows. `VACUUM FULL` rewrites a table with
only its live rows; every row you can SELECT before is still there after.
It does take an exclusive lock on each table while rewriting it (seconds to a
few minutes here), so run it outside 01:00-05:00 UTC when retention and the
job pipeline run.

Default is a read-only report. Nothing changes without a flag.

Run it inside Railway so no credentials leave the platform:
    railway ssh --service applyluma-celery-worker
    python scripts/compact_database.py              # report only
    python scripts/compact_database.py --vacuum     # compact the job tables
    python scripts/compact_database.py --tune       # lower shared_buffers / max_connections
`--tune` only writes postgresql.auto.conf; restart the Postgres service for
it to take effect, then re-run the report to confirm the new values.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

# Tables retention churns through. Fixed list: the script never takes table
# names from the command line.
VACUUM_TABLES = ("raw_job_postings", "extracted_keywords", "job_matching_scores")

# Web, worker and beat each get SQLAlchemy's default pool (5 + 10 overflow),
# about 45 at the theoretical peak, plus the scrapers' own psycopg2
# connections and a console or two. 60 leaves headroom; idle slots are cheap.
TUNED_SETTINGS = {"shared_buffers": "128MB", "max_connections": "60"}

# VACUUM FULL needs an exclusive lock. If a long task already holds the table,
# waiting for it would queue every later query (Discover) behind the vacuum,
# so give up on that table instead and report it.
LOCK_TIMEOUT = "10s"

REPORT_SQL = text(
    """
    SELECT relname,
           n_live_tup,
           n_dead_tup,
           pg_total_relation_size(relid) AS bytes,
           pg_size_pretty(pg_total_relation_size(relid)) AS size
    FROM pg_stat_user_tables
    ORDER BY pg_total_relation_size(relid) DESC
    LIMIT 15
    """
)


def _database_url() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        )
    except Exception:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)
    return url.replace("postgres://", "postgresql://", 1)


def report(conn: Connection) -> int:
    print(f"{'table':<32}{'live rows':>12}{'dead rows':>12}{'size':>12}")
    for row in conn.execute(REPORT_SQL):
        print(f"{row.relname:<32}{row.n_live_tup:>12}{row.n_dead_tup:>12}{row.size:>12}")
    total = conn.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
    print(f"\ndatabase size: {total / 1024 / 1024:.0f} MB")
    for name in TUNED_SETTINGS:
        print(f"{name}: {conn.execute(text(f'SHOW {name}')).scalar_one()}")
    return int(total)


def vacuum(conn: Connection) -> None:
    quote = conn.dialect.identifier_preparer.quote
    for table in VACUUM_TABLES:
        exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one()
        if exists is None:
            print(f"skip {table}: not found")
            continue
        print(f"VACUUM (FULL, ANALYZE) {table} ...", flush=True)
        try:
            conn.execute(text(f"VACUUM (FULL, ANALYZE) {quote(table)}"))
        except OperationalError as exc:
            if "lock timeout" not in str(exc):
                raise
            print(f"  skipped {table}: busy (lock not free within {LOCK_TIMEOUT}), try again later")


def tune(conn: Connection) -> None:
    for name, value in TUNED_SETTINGS.items():
        print(f"ALTER SYSTEM SET {name} = '{value}'")
        conn.execute(text(f"ALTER SYSTEM SET {name} = '{value}'"))
    print("\nRestart the Postgres service, then re-run without flags to confirm.")
    print("If the values did not change, the image sets them on its command line.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--vacuum", action="store_true", help="VACUUM FULL the job tables (locks each briefly)"
    )
    parser.add_argument(
        "--tune", action="store_true", help="lower shared_buffers and max_connections"
    )
    args = parser.parse_args()

    engine = create_engine(_database_url())
    # VACUUM and ALTER SYSTEM refuse to run inside a transaction block.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET lock_timeout = '{LOCK_TIMEOUT}'"))
        before = report(conn)
        if args.vacuum:
            print()
            vacuum(conn)
            print()
            after = report(conn)
            print(f"\nreclaimed: {(before - after) / 1024 / 1024:.0f} MB")
        if args.tune:
            print()
            tune(conn)


if __name__ == "__main__":
    main()
