-- Migration 20260613153000_create_ingest_queue
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Banco compartilhado por 3 apps; aplicar novas migrations só via MCP apply_migration.

-- Ingestão em segundo plano do bot ("modo rápido"): a Muri manda as fotos e o
-- processamento (IA + insert) acontece depois, drenado por um worker.
-- ingest_queue = a fila; telegram_prefs = preferências por chat (ex.: modo rápido).

create table if not exists ingest_queue (
  id           uuid primary key default gen_random_uuid(),
  chat_id      bigint not null,
  file_id      text not null,                 -- file_id durável do Telegram (getFile no worker)
  status       text not null default 'pending'
               check (status in ('pending', 'processing', 'done', 'failed')),
  error        text,
  notified     boolean not null default false, -- já avisou o chat sobre este resultado?
  started_at   timestamptz,                    -- quando foi reivindicado (p/ reaper de travados)
  created_at   timestamptz default now(),
  processed_at timestamptz
);
create index if not exists ingest_queue_status_idx on ingest_queue (status);
create index if not exists ingest_queue_chat_idx on ingest_queue (chat_id);

create table if not exists telegram_prefs (
  chat_id    bigint primary key,
  fast_mode  boolean not null default false,
  updated_at timestamptz default now()
);

-- Claim atômico de jobs: pega pendentes E reivindica de volta os 'processing'
-- presos há mais de 5 min (worker que morreu no meio, ex.: timeout da função).
-- FOR UPDATE SKIP LOCKED evita processamento duplo se dois ticks se sobrepuserem.
create or replace function claim_ingest_jobs(n int)
returns setof ingest_queue
language sql
as $$
  update ingest_queue q
     set status = 'processing', started_at = now()
   where q.id in (
     select id from ingest_queue
      where status = 'pending'
         or (status = 'processing' and started_at < now() - interval '5 minutes')
      order by created_at
      limit n
      for update skip locked
   )
  returning q.*;
$$;
