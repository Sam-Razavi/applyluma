-- Salary percentiles (p25 / p50 / p75 / p90) broken out by four dimensions:
-- skill, location, company, and employment_type.
-- Only postings where both salary_min and salary_max are non-null are included
-- so the midpoint used for all percentile calculations is meaningful.
-- Rows with fewer than the minimum sample size are excluded.

with jobs as (
    select
        job_id,
        company_name,
        location,
        employment_type,
        salary_min,
        salary_max,
        salary_midpoint,
        skill_array,
        scrape_date
    from {{ ref('fct_job_postings') }}
    where salary_min is not null
      and salary_max is not null
),

-- ── By skill ─────────────────────────────────────────────────────────────────
by_skill as (
    select
        'skill'                                                                       as breakdown_type,
        skill                                                                         as breakdown_value,
        count(distinct job_id)                                                        as job_count,
        round(percentile_cont(0.25) within group (order by salary_midpoint))          as p25_salary,
        round(percentile_cont(0.50) within group (order by salary_midpoint))          as p50_salary,
        round(percentile_cont(0.75) within group (order by salary_midpoint))          as p75_salary,
        round(percentile_cont(0.90) within group (order by salary_midpoint))          as p90_salary,
        round(avg(salary_midpoint))                                                   as avg_salary,
        round(min(salary_min))                                                        as min_salary_floor,
        round(max(salary_max))                                                        as max_salary_ceiling
    from jobs, unnest(skill_array) as skill
    where skill_array is not null
      and array_length(skill_array, 1) > 0
    group by skill
    having count(distinct job_id) >= 5
),

-- ── By location ───────────────────────────────────────────────────────────────
by_location as (
    select
        'location'                                                                    as breakdown_type,
        location                                                                      as breakdown_value,
        count(distinct job_id)                                                        as job_count,
        round(percentile_cont(0.25) within group (order by salary_midpoint))          as p25_salary,
        round(percentile_cont(0.50) within group (order by salary_midpoint))          as p50_salary,
        round(percentile_cont(0.75) within group (order by salary_midpoint))          as p75_salary,
        round(percentile_cont(0.90) within group (order by salary_midpoint))          as p90_salary,
        round(avg(salary_midpoint))                                                   as avg_salary,
        round(min(salary_min))                                                        as min_salary_floor,
        round(max(salary_max))                                                        as max_salary_ceiling
    from jobs
    where location != 'Unknown'
    group by location
    having count(distinct job_id) >= 5
),

-- ── By company ────────────────────────────────────────────────────────────────
by_company as (
    select
        'company'                                                                     as breakdown_type,
        company_name                                                                  as breakdown_value,
        count(distinct job_id)                                                        as job_count,
        round(percentile_cont(0.25) within group (order by salary_midpoint))          as p25_salary,
        round(percentile_cont(0.50) within group (order by salary_midpoint))          as p50_salary,
        round(percentile_cont(0.75) within group (order by salary_midpoint))          as p75_salary,
        round(percentile_cont(0.90) within group (order by salary_midpoint))          as p90_salary,
        round(avg(salary_midpoint))                                                   as avg_salary,
        round(min(salary_min))                                                        as min_salary_floor,
        round(max(salary_max))                                                        as max_salary_ceiling
    from jobs
    group by company_name
    having count(distinct job_id) >= 3
),

-- ── By employment type ────────────────────────────────────────────────────────
by_employment_type as (
    select
        'employment_type'                                                             as breakdown_type,
        employment_type                                                               as breakdown_value,
        count(distinct job_id)                                                        as job_count,
        round(percentile_cont(0.25) within group (order by salary_midpoint))          as p25_salary,
        round(percentile_cont(0.50) within group (order by salary_midpoint))          as p50_salary,
        round(percentile_cont(0.75) within group (order by salary_midpoint))          as p75_salary,
        round(percentile_cont(0.90) within group (order by salary_midpoint))          as p90_salary,
        round(avg(salary_midpoint))                                                   as avg_salary,
        round(min(salary_min))                                                        as min_salary_floor,
        round(max(salary_max))                                                        as max_salary_ceiling
    from jobs
    where employment_type != 'unknown'
    group by employment_type
    having count(distinct job_id) >= 3
)

select * from by_skill
union all
select * from by_location
union all
select * from by_company
union all
select * from by_employment_type
