with events as (
    select * from {{ ref('stg_events') }}
)

select
    user_id,
    count(*) as total_events,
    sum(case when event_type = 'purchase' then 1 else 0 end) as total_purchases,
    sum(case when event_type = 'refund' then 1 else 0 end) as total_refunds,
    sum(case when event_type = 'purchase' then amount else 0 end)
        as gross_spend,
    min(event_at) as first_seen_at,
    max(event_at) as last_seen_at
from events
group by user_id
