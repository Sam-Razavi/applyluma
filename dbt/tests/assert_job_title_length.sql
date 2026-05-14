-- Job titles should be reasonably long (at least 3 characters)
select
    job_id,
    job_title
from {{ ref('stg_job_postings') }}
where length(job_title) < 3
