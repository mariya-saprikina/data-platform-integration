with events as (
    select * from {{ ref('stg_events') }}
),

user_activity as (
    select * from {{ ref('int_user_activity') }}
)

select
    cast(event_at as date)              as event_date,
    e.user_id,
    u.total_purchases,
    u.total_refunds,
    sum(case when e.event_type = 'purchase' then e.amount else 0 end) as daily_revenue,
    sum(case when e.event_type = 'refund'   then e.amount else 0 end) as daily_refunds
from events e
join user_activity u on e.user_id = u.user_id
where e.event_type in ('purchase', 'refund')
group by cast(event_at as date), e.user_id, u.total_purchases, u.total_refunds
