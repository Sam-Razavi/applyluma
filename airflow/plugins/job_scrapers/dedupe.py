"""Cross-source, rolling-window deduplication for raw_job_postings.

A posting scraped today is marked as a duplicate when a live (non-duplicate)
posting with the same normalised title, company, and location was already
scraped within the window — regardless of source. The oldest posting wins.
Location is part of the key so the same role advertised in different cities
is never collapsed into one posting.

Only today's rows are ever marked by the daily run; historical cleanup is a
one-off (see scripts/backfill_duplicates.py).
"""
from __future__ import annotations

from typing import Any

DEDUPE_WINDOW_DAYS = 14

MARK_TODAYS_DUPLICATES_SQL = f"""
    WITH ranked AS (
        SELECT
            id,
            scraped_at,
            ROW_NUMBER() OVER (
                PARTITION BY
                    lower(trim(title)),
                    lower(trim(company)),
                    coalesce(lower(trim(location)), '')
                ORDER BY scraped_at ASC
            ) AS rn
        FROM raw_job_postings
        WHERE scraped_at >= CURRENT_DATE - INTERVAL '{DEDUPE_WINDOW_DAYS} days'
          AND is_duplicate = false
    )
    UPDATE raw_job_postings
    SET is_duplicate = true
    WHERE id IN (
        SELECT id FROM ranked
        WHERE rn > 1
          AND DATE(scraped_at) = CURRENT_DATE
    )
"""


def mark_todays_duplicates(conn: Any) -> int:
    """Mark today's duplicate postings on an open psycopg2 connection.

    Returns the number of rows marked.
    """
    with conn, conn.cursor() as cur:
        cur.execute(MARK_TODAYS_DUPLICATES_SQL)
        return cur.rowcount
