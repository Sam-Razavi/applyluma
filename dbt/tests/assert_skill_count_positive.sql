-- skill_count in fct_job_postings should not be negative
select
    job_id,
    skill_count
from {{ ref('fct_job_postings') }}
where skill_count < 0
