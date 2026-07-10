with source as (
    select * from {{ source('raw', 'events') }}
)

select
    event_id,
    user_id,
    event_type,
    product_id,
    cast(amount as decimal(10, 2)) as amount,
    cast(ts as timestamp) as event_at
from source
