-- Enrich deduplicated jobs with a parsed skill array and skill count.
-- The extract_skills macro is called once in a CTE so the expensive
-- regex block runs exactly once per row.

with deduped as (
    select * from {{ ref('int_jobs_deduplicated') }}
),

skills_extracted as (
    select
        *,
        {{ extract_skills('job_description') }} as skill_array
    from deduped
)

select
    *,
    coalesce(array_length(skill_array, 1), 0) as skill_count
from skills_extracted
