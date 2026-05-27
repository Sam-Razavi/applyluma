with jobs as (
    select
        company_name,
        remote_allowed,
        employment_type,
        salary_min,
        salary_max,
        scraped_at
    from {{ ref('int_jobs_with_skills') }}
),

aggregated as (
    select
        company_name,
        count(*)                                                                as total_jobs_posted,
        count(*) filter (where remote_allowed)                                  as remote_jobs,
        round(
            count(*) filter (where remote_allowed)::numeric
            / nullif(count(*), 0) * 100,
            1
        )                                                                       as remote_percentage,
        round(avg(salary_min) filter (where salary_min is not null))            as avg_salary_min,
        round(avg(salary_max) filter (where salary_max is not null))            as avg_salary_max,
        min(scraped_at)::date                                                   as first_seen_date,
        max(scraped_at)::date                                                   as last_seen_date,
        mode() within group (order by employment_type)                          as most_common_employment_type
    from jobs
    group by company_name
)

select
    md5(lower(company_name))        as company_id,
    company_name,
    total_jobs_posted,
    remote_jobs,
    remote_percentage,
    avg_salary_min,
    avg_salary_max,
    (avg_salary_min is not null
        or avg_salary_max is not null)  as has_salary_data,
    first_seen_date,
    last_seen_date,
    most_common_employment_type,
    current_timestamp                   as dbt_updated_at
from aggregated
