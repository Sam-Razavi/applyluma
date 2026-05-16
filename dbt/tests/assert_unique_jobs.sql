-- Singular test: returns rows when duplicates exist in the fact table.
-- dbt fails this test when any rows are returned.
-- A duplicate: same company + normalised_title + scrape_date.

select
    lower(company_name)     as company,
    normalised_title,
    scrape_date,
    count(*)                as duplicate_count
from {{ ref('fct_job_postings') }}
group by 1, 2, 3
having count(*) > 1
