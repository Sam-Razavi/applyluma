"""One-off backfill: fix substring-matching false positives in extracted_keywords.

The extract_keywords DAG used to tag job postings using naive substring
matching (see airflow/dags/extract_keywords_dag.py before the boundary-safe
fix), so keywords like "Go" matched inside "Google", "Java" matched inside
"JavaScript", and "SQL" matched inside "PostgreSQL"/"MySQL"/"NoSQL" — all
stored at confidence 1.0. It also could never match symbol-suffixed keywords
like "C++"/"C#" (once the DAG moved to \\b-based boundaries), so those rows
were simply missing.

This script re-runs the fixed extractor (job_scrapers.keyword_extraction,
stdlib-only, no Airflow install needed) against raw_job_postings.description
for every posting that has at least one extracted_keywords row whose keyword
is in the curated SIMPLE_SKILLS set, and:
  - deletes rows for keywords that no longer match (false positives), and
  - inserts rows for keywords that now match but are missing (e.g. C++/C#).

Only rows whose keyword is in SIMPLE_SKILLS are ever touched — other code
paths (e.g. the Phase 10A KeywordExtractor) write additional keyword rows to
the same table and are left untouched.

Usage (against Railway, from the project root):
    DATABASE_URL=postgresql://... python scripts/backfill_keyword_false_positives.py            # dry run
    DATABASE_URL=postgresql://... python scripts/backfill_keyword_false_positives.py --apply    # apply changes

Use the public Railway proxy URL (see CLAUDE.md) for DATABASE_URL when
running locally — the `.railway.internal` host is only reachable inside
Railway.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "airflow", "plugins"))

from job_scrapers.keyword_extraction import SIMPLE_SKILLS, extract_keywords_simple  # noqa: E402

BATCH_SIZE = 500

_KEYWORD_SET = {keyword for keyword, _ in SIMPLE_SKILLS}

SELECT_CANDIDATE_IDS_SQL = """
    SELECT DISTINCT rjp.id
    FROM raw_job_postings rjp
    JOIN extracted_keywords ek ON ek.raw_job_posting_id = rjp.id
    WHERE ek.keyword = ANY(%s)
    ORDER BY rjp.id
"""

SELECT_POSTINGS_SQL = """
    SELECT id, description
    FROM raw_job_postings
    WHERE id = ANY(%s)
"""

SELECT_EXISTING_SQL = """
    SELECT raw_job_posting_id, keyword, keyword_type
    FROM extracted_keywords
    WHERE raw_job_posting_id = ANY(%s)
      AND keyword = ANY(%s)
"""

DELETE_SQL = """
    DELETE FROM extracted_keywords
    WHERE raw_job_posting_id = %s AND keyword = %s AND keyword_type = %s
"""

INSERT_SQL = """
    INSERT INTO extracted_keywords
        (raw_job_posting_id, keyword, keyword_type, confidence_score, frequency)
    VALUES %s
    ON CONFLICT (raw_job_posting_id, keyword, keyword_type) DO NOTHING
"""


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the deletes/inserts. Without this flag, only report counts.",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_CANDIDATE_IDS_SQL, (list(_KEYWORD_SET),))
            candidate_ids = [row[0] for row in cur.fetchall()]

        print(f"{len(candidate_ids)} posting(s) have at least one curated-keyword row")

        postings_scanned = 0
        delete_counts: Counter[str] = Counter()
        insert_counts: Counter[str] = Counter()
        total_deleted = 0
        total_inserted = 0

        for batch_ids in _batched(candidate_ids, BATCH_SIZE):
            with conn.cursor() as cur:
                cur.execute(SELECT_POSTINGS_SQL, (batch_ids,))
                postings = cur.fetchall()

                cur.execute(SELECT_EXISTING_SQL, (batch_ids, list(_KEYWORD_SET)))
                existing = {(row[0], row[1], row[2]) for row in cur.fetchall()}

            to_delete: list[tuple] = []
            to_insert: list[tuple] = []

            for job_id, description in postings:
                postings_scanned += 1
                current_keywords = extract_keywords_simple(description or "")
                current_matched = {
                    (keyword, kw_type) for keyword, kw_type, _confidence, _freq in current_keywords
                }

                existing_curated = {
                    (kw, kw_type)
                    for (jid, kw, kw_type) in existing
                    if jid == job_id and kw in _KEYWORD_SET
                }

                for kw, kw_type in existing_curated - current_matched:
                    to_delete.append((job_id, kw, kw_type))
                    delete_counts[kw] += 1

                for keyword, kw_type, confidence, freq in current_keywords:
                    if (keyword, kw_type) not in existing_curated:
                        to_insert.append((str(job_id), keyword, kw_type, confidence, freq))
                        insert_counts[keyword] += 1

            if args.apply:
                with conn, conn.cursor() as cur:
                    for job_id, kw, kw_type in to_delete:
                        cur.execute(DELETE_SQL, (job_id, kw, kw_type))
                    if to_insert:
                        psycopg2.extras.execute_values(cur, INSERT_SQL, to_insert)

            total_deleted += len(to_delete)
            total_inserted += len(to_insert)

        verb = "Deleted" if args.apply else "Would delete"
        insert_verb = "Inserted" if args.apply else "Would insert"

        print(f"Postings scanned: {postings_scanned}")
        print(f"{verb} {total_deleted} false-positive row(s):")
        for kw, count in delete_counts.most_common():
            print(f"  {kw}: {count}")
        print(f"{insert_verb} {total_inserted} newly-matched row(s):")
        for kw, count in insert_counts.most_common():
            print(f"  {kw}: {count}")

        if not args.apply:
            print("Dry run — re-run with --apply to write changes.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
