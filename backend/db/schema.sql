create table if not exists search_cache (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  source text not null,           -- 'news_rss' | 'yfinance' | 'chart' | 'summary'
  payload jsonb not null,
  fetched_at timestamptz not null default now()
);
create index if not exists idx_search_cache_lookup on search_cache (ticker, source, fetched_at desc);

create table if not exists training_data (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  headline text not null,
  headline_date date not null,
  price_up_next_day boolean,
  created_at timestamptz not null default now()
);

create table if not exists ticker_resolution_cache (
  id uuid primary key default gen_random_uuid(),
  raw_query text not null unique,
  resolved_ticker text not null,
  resolved_at timestamptz not null default now()
);
