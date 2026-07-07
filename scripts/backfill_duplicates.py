"""One-off backfill: mark historical cross-source duplicates in raw_job_postings.

Applies the same rolling-window rule the daily DAGs now use (see
airflow/plugins/job_scrapers/dedupe.py) to rows scraped before the rule
existed: a posting is marked as a duplicate when an older live posting with
the same normalised title, company, and location was scraped within the
preceding window. The oldest posting always survives.

Marked rows disappear from the Discover feed, analytics, and the match-scoring
batch. Saved jobs and applications reference postings by id without an
is_duplicate filter, so nothing a user has saved or applied to breaks.

Note: the duplicate check runs against a single snapshot, so in a chain of
near-identical postings (A -> B -> C, each within the window of the previous)
every posting after the first is marked, even if C is outside A's window.
That is the conservative outcome we want for a backfill.

Usage (against Railway, from the project root):
    DATABASE_URL=postgresql://... python scripts/backfill_duplicates.py            # dry run
    DATABASE_URL=postgresql://... python scripts/backfill_duplicates.py --apply    # mark rows
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg2

WINDOW_DAYS = 14  # keep in sync with job_scrapers.dedupe.DEDUPE_WINDOW_DAYS

_DUPLICATE_PREDICATE = f"""
    r.is_duplicate = false
    AND EXISTS (
        SELECT 1
        FROM raw_job_postings e
        WHERE e.is_duplicate = false
          AND e.id <> r.id
          AND e.scraped_at < r.scraped_at
          AND e.scraped_at >= r.scraped_at - INTERVAL '{WINDOW_DAYS} days'
          AND lower(trim(e.title)) = lower(trim(r.title))
          AND lower(trim(e.company)) = lower(trim(r.company))
          AND coalesce(lower(trim(e.location)), '') = coalesce(lower(trim(r.location)), '')
    )
"""

COUNT_SQL = f"SELECT COUNT(*) FROM raw_job_postings r WHERE {_DUPLICATE_PREDICATE}"

UPDATE_SQL = f"""
    UPDATE raw_job_postings r
    SET is_duplicate = true
    WHERE {_DUPLICATE_PREDICATE}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually mark the rows. Without this flag, only report the count.",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            count = cur.fetchone()[0]
        print(f"{count} historical duplicate posting(s) found (window: {WINDOW_DAYS} days)")

        if not args.apply:
            print("Dry run — re-run with --apply to mark them.")
            return 0

        with conn, conn.cursor() as cur:
            cur.execute(UPDATE_SQL)
            print(f"Marked {cur.rowcount} posting(s) as duplicates.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
