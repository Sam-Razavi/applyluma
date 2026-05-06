with jobs as (
    select
        job_id,
        skill_array,
        salary_min,
        salary_max,
        scraped_at::date as scrape_date
    from {{ ref('int_jobs_with_skills') }}
    where skill_array is not null
      and array_length(skill_array, 1) > 0
),

-- One row per (job, skill) pair
unnested as (
    select
        job_id,
        skill,
        salary_min,
        salary_max,
        scrape_date
    from jobs, unnest(skill_array) as skill
),

aggregated as (
    select
        skill,
        count(distinct job_id)                                                  as total_job_mentions,
        round(avg(salary_min) filter (where salary_min is not null))            as avg_salary_min,
        round(avg(salary_max) filter (where salary_max is not null))            as avg_salary_max,
        count(distinct job_id) filter (
            where scrape_date >= current_date - interval '7 days'
        )                                                                       as mentions_this_week,
        count(distinct job_id) filter (
            where scrape_date between current_date - interval '14 days'
                                  and current_date - interval '8 days'
        )                                                                       as mentions_last_week
    from unnested
    group by skill
)

select
    md5(skill)                  as skill_id,
    skill                       as skill_name,
    total_job_mentions,
    avg_salary_min,
    avg_salary_max,
    mentions_this_week,
    mentions_last_week,
    case
        when mentions_last_week = 0
            then 100.0
        else round(
            (mentions_this_week - mentions_last_week)::numeric
            / mentions_last_week * 100,
            1
        )
    end                         as trending_score_pct,
    current_timestamp           as dbt_updated_at
from aggregated
