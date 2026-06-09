-- Migration 20260607224842_create_telegram_sessions
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).

create table if not exists telegram_sessions (
  chat_id    bigint primary key,
  garment_id uuid references garments(id) on delete set null,
  step       text not null,
  draft      jsonb default '{}'::jsonb,
  updated_at timestamptz default now()
);
