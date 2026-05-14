-- Every scraped job must at minimum have a title and a company.
select
    id
from {{ ref('stg_job_postings') }}
where 
    title is null 
    or company_name is null