-- remote_percentage should be between 0 and 100
select
    metric_date,
    remote_percentage
from {{ ref('fct_daily_metrics') }}
where remote_percentage < 0 or remote_percentage > 100
