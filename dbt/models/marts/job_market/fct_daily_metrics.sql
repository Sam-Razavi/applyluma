with jobs as (
    select * from {{ ref('fct_job_postings') }}
),

-- ── Base stats ────────────────────────────────────────────────────────────────
base_stats as (
    select
        scrape_date                                                                     as metric_date,
        count(*)                                                                        as total_jobs,
        count(*) filter (where remote_allowed)                                          as remote_jobs,
        round(
            count(*) filter (where remote_allowed)::numeric
            / nullif(count(*), 0) * 100, 1
        )                                                                               as remote_percentage,
        count(*) filter (where is_senior_role)                                          as senior_role_count,
        count(*) filter (where is_junior_role)                                          as junior_role_count,
        count(*) filter (where is_management_role)                                      as management_role_count,
        round(avg(salary_midpoint) filter (where salary_midpoint is not null))          as avg_salary_midpoint,
        round(avg(salary_min)      filter (where salary_min      is not null))          as avg_salary_min,
        round(avg(salary_max)      filter (where salary_max      is not null))          as avg_salary_max,
        round(avg(skill_count), 1)                                                      as avg_skills_per_job
    from jobs
    group by scrape_date
),

-- ── Top 10 companies per day ──────────────────────────────────────────────────
company_counts as (
    select
        scrape_date,
        company_name,
        count(*)                                                                        as job_count,
        rank() over (partition by scrape_date order by count(*) desc)                  as company_rank
    from jobs
    group by scrape_date, company_name
),

top_companies_agg as (
    select
        scrape_date,
        jsonb_agg(
            jsonb_build_object('company', company_name, 'count', job_count)
            order by company_rank
        )                                                                               as top_10_companies
    from company_counts
    where company_rank <= 10
    group by scrape_date
),

-- ── Employment type breakdown ─────────────────────────────────────────────────
employment_breakdown as (
    select
        scrape_date,
        jsonb_object_agg(
            coalesce(employment_type, 'unknown'),
            job_count
        )                                                                               as employment_type_breakdown
    from (
        select scrape_date, employment_type, count(*) as job_count
        from jobs
        group by scrape_date, employment_type
    ) t
    group by scrape_date
),

-- ── Top 10 skills per day ─────────────────────────────────────────────────────
skill_counts as (
    select
        scrape_date,
        skill,
        count(*)                                                                        as mention_count,
        rank() over (partition by scrape_date order by count(*) desc)                  as skill_rank
    from jobs, unnest(skill_array) as skill
    where skill_array is not null
    group by scrape_date, skill
),

top_skills_agg as (
    select
        scrape_date,
        jsonb_agg(
            jsonb_build_object('skill', skill, 'count', mention_count)
            order by skill_rank
        )                                                                               as top_10_skills
    from skill_counts
    where skill_rank <= 10
    group by scrape_date
)

select
    bs.metric_date,
    bs.total_jobs,
    bs.remote_jobs,
    bs.remote_percentage,
    bs.senior_role_count,
    bs.junior_role_count,
    bs.management_role_count,
    bs.avg_salary_midpoint,
    bs.avg_salary_min,
    bs.avg_salary_max,
    bs.avg_skills_per_job,
    tca.top_10_companies,
    ebd.employment_type_breakdown,
    tsa.top_10_skills,
    current_timestamp                                                                   as dbt_updated_at
from base_stats bs
left join top_companies_agg  tca on bs.metric_date = tca.scrape_date
left join employment_breakdown ebd on bs.metric_date = ebd.scrape_date
left join top_skills_agg     tsa on bs.metric_date = tsa.scrape_date
