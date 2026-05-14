-- If salary_min is greater than salary_max, there is a scraping or parsing anomaly.
select
    id,
    salary_min,
    salary_max
from {{ ref('stg_job_postings') }}
where salary_min is not null 
  and salary_max is not null 
  and salary_min > salary_max