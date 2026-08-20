-- Supabase SQL Schema for Embeddable Stock Research Module

-- 1. Search & Scraping Cache (TTL Caching)
create table if not exists search_cache (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  source text not null,           -- 'indian_news_scraper' | 'summary' | 'chart_1m' | etc.
  payload jsonb not null,
  fetched_at timestamptz not null default now()
);
create index if not exists idx_search_cache_lookup on search_cache (ticker, source, fetched_at desc);
alter table search_cache disable row level security;

-- 2. Training Data for Scikit-Learn Headline Sentiment Models
create table if not exists training_data (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  headline text not null,
  headline_date date not null,
  price_up_next_day boolean,
  created_at timestamptz not null default now()
);
create index if not exists idx_training_data_ticker on training_data (ticker, headline_date desc);
alter table training_data disable row level security;

-- 3. Ticker Resolution Entity Cache
create table if not exists ticker_resolution_cache (
  id uuid primary key default gen_random_uuid(),
  raw_query text not null unique,
  resolved_ticker text not null,
  resolved_at timestamptz not null default now()
);
create index if not exists idx_ticker_resolution on ticker_resolution_cache (raw_query);
alter table ticker_resolution_cache disable row level security;

-- 4. Price Threshold Alerts (Mobile Notifications)
create table if not exists price_alerts (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  target_price numeric not null,
  condition text not null,         -- 'above' | 'below'
  currency_symbol text default '$',
  status text default 'active',    -- 'active' | 'triggered' | 'dismissed'
  user_id text default 'guest',
  created_at timestamptz not null default now(),
  triggered_at timestamptz
);
create index if not exists idx_price_alerts_status on price_alerts (status, user_id);
alter table price_alerts disable row level security;

-- 5. Chat & Q&A Logging
create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(),
  host_user_id text,
  created_at timestamptz not null default now()
);
alter table chat_sessions disable row level security;

create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references chat_sessions(id) on delete cascade,
  role text not null,             -- 'user' | 'assistant'
  content text not null,
  created_at timestamptz not null default now()
);
alter table chat_messages disable row level security;
