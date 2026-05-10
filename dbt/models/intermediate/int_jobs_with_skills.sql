-- Enrich deduplicated jobs with a parsed skill array and skill count.
-- The extract_skills macro is called once in a CTE so the expensive
-- regex block runs exactly once per row.

with deduped as (
    select * from {{ ref('int_jobs_deduplicated') }}
),

skills_extracted as (
    select
        *,
        case
            when jsonb_typeof(extracted_skills) = 'array'
                 and jsonb_array_length(extracted_skills) > 0
                then (
                    select array_agg(lower(trim(skill_text)))
                    from jsonb_array_elements_text(extracted_skills) as extracted(skill_text)
                    where nullif(trim(skill_text), '') is not null
                )
            else {{ extract_skills('job_description') }}
        end as skill_array
    from deduped
)

select
    *,
    coalesce(array_length(skill_array, 1), 0) as skill_count
from skills_extracted
