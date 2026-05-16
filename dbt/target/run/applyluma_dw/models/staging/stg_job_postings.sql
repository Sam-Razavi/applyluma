
  create view "applyluma"."analytics"."stg_job_postings__dbt_tmp"
    
    
  as (
    with source as (
    select * from "applyluma"."public"."raw_job_postings"
),

cleaned as (
    select
        id::text                                                        as job_id,
        source                                                          as job_source,
        job_id_external,
        trim(title)                                                     as job_title,
        trim(company)                                                   as company_name,
        coalesce(nullif(trim(location), ''), 'Unknown')                 as location,
        description                                                     as job_description,
        url                                                             as job_url,
        salary_min,
        salary_max,
        lower(coalesce(nullif(trim(employment_type), ''), 'unknown'))   as employment_type,
        coalesce(remote_allowed, false)                                 as remote_allowed,
        extracted_skills,
        coalesce(is_duplicate, false)                                   as is_duplicate,
        raw_data,
        scraped_at,
        created_at,
        date_trunc('day', scraped_at)::date                            as scrape_date
    from source
    where
        title       is not null and trim(title)       != ''
        and company is not null and trim(company)     != ''
        and description is not null and length(description) > 50
        and url     is not null and url               != ''
)

select * from cleaned
  );