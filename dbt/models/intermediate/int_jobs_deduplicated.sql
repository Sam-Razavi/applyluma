-- Two-pass dedup:
--   Pass 1 (Airflow): rows with is_duplicate = true are dropped here.
--   Pass 2 (dbt): same company + normalised title → keep the newest record.
-- Normalisation strips common seniority tokens so "Senior Python Dev"
-- and "Python Dev" collapse to the same key.

with staged as (
    select * from {{ ref('stg_job_postings') }}
),

normalised as (
    select
        *,
        lower(
            trim(
                regexp_replace(
                    regexp_replace(
                        job_title,
                        '\s*(senior|sr\.?|junior|jr\.?|lead|staff|principal|associate|mid-level|entry.level|intern)\s*',
                        ' ', 'gi'
                    ),
                    '\s{2,}', ' ', 'g'
                )
            )
        ) as normalised_title
    from staged
    where not is_duplicate
),

ranked as (
    select
        *,
        row_number() over (
            partition by lower(company_name), normalised_title
            order by scraped_at desc
        ) as dedup_rank
    from normalised
)

select
    job_id,
    job_source,
    job_id_external,
    job_title,
    normalised_title,
    company_name,
    location,
    job_description,
    job_url,
    salary_min,
    salary_max,
    employment_type,
    remote_allowed,
    extracted_skills,
    raw_data,
    scraped_at,
    created_at,
    scrape_date
from ranked
where dedup_rank = 1
