-- Jobs should not have a posted date in the future (allowing a 1-day timezone buffer).
-- Prevents corrupt scraper dates from polluting the time-series charts.
select
    id,
    posted_date
from {{ ref('stg_job_postings') }}
where posted_date is not null
  and posted_date > current_date + interval '1 day'