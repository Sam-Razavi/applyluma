{% test is_valid_url(model, column_name) %}

with validation_errors as (
    select
        {{ column_name }} as url
    from {{ model }}
    where {{ column_name }} not like 'http%'
)

select *
from validation_errors

{% endtest %}
