{{
    config(
        materialized = 'incremental',
        unique_key   = 'job_id',
        on_schema_change = 'sync_all_columns'
    )
}}

with jobs as (
    select * from {{ ref('int_jobs_with_skills') }}
    {% if is_incremental() %}
        -- Only process rows scraped since the last run
        where scraped_at > (select max(scraped_at) from {{ this }})
    {% endif %}
),

companies as (
    select company_id, company_name from {{ ref('dim_companies') }}
)

select
    j.job_id,
    j.job_source,
    j.job_id_external,
    j.job_title,
    j.normalised_title,
    c.company_id,
    j.company_name,
    j.location,
    j.job_url,
    j.salary_min,
    j.salary_max,
    case
        when j.salary_min is not null and j.salary_max is not null
            then (j.salary_min + j.salary_max) / 2
        else coalesce(j.salary_min, j.salary_max)
    end                                                                     as salary_midpoint,
    j.employment_type,
    j.remote_allowed,
    j.skill_array,
    j.skill_count,
    j.scraped_at,
    j.created_at,
    j.scrape_date,
    (current_date - j.scrape_date)                                          as days_since_posted,
    -- Role-level flags derived from title keywords
    (j.job_title ~* '\m(senior|sr\.?|lead|principal|staff|director|vp|head)\M')  as is_senior_role,
    (j.job_title ~* '\m(manager|director|head of|vp|chief|cto|cpo|ceo)\M')       as is_management_role,
    (j.job_title ~* '\m(junior|jr\.?|entry.level|associate|intern)\M')            as is_junior_role,
    current_timestamp                                                       as dbt_updated_at
from jobs j
left join companies c using (company_name)
