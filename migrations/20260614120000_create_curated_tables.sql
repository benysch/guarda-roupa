-- Migration 20260614120000_create_curated_tables
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Banco compartilhado por 3 apps; aplicar novas migrations só via MCP apply_migration.

-- Pré-computação de looks/mala: a curadoria com "bom gosto" deixa de rodar em tempo real
-- (estilista Gemini) e passa a ser gerada offline (pelo Claude Code) e cacheada aqui.
-- O site lê estas tabelas; combo sem curadoria cai no motor de regras (instantâneo, sem IA).

-- Looks curados por combinação (ocasião × estação × clima), com K variações p/ "montar outro".
create table if not exists curated_looks (
  id                uuid primary key default gen_random_uuid(),
  occasion          text,
  season            text,
  temperature       text,
  variant           int not null default 0,
  garment_ids       uuid[] not null,
  rationale         text,
  missing           text[] default '{}',
  garment_signature text,            -- assinatura do acervo no momento da geração (staleness)
  generated_at      timestamptz default now()
);
create index if not exists curated_looks_combo_idx on curated_looks (occasion, season, temperature);

-- Cápsulas de viagem curadas (payload = resultado pronto: grupos + looks por dia).
create table if not exists curated_capsules (
  id                uuid primary key default gen_random_uuid(),
  days              int not null,
  occasion          text,
  night             text,
  season            text,
  temperature       text,
  payload           jsonb not null,
  garment_signature text,
  generated_at      timestamptz default now()
);
create index if not exists curated_capsules_combo_idx
  on curated_capsules (days, occasion, night, season, temperature);

-- Registro de combos pedidos sem cache (a parte "sob demanda": prioriza o que gerar depois).
create table if not exists look_requests (
  id             uuid primary key default gen_random_uuid(),
  kind           text not null,    -- 'look' | 'capsule'
  combo          text not null,    -- chave textual do combo
  count          int not null default 1,
  last_requested timestamptz default now(),
  unique (kind, combo)
);
