-- Feedback gostei/não gostei nas composições, pra treinar a curadoria do estilista.
alter table curated_looks
  add column if not exists suppressed boolean not null default false;

create table if not exists look_feedback (
  id uuid primary key default gen_random_uuid(),
  curated_look_id uuid references curated_looks(id) on delete set null,
  garment_ids uuid[] not null default '{}',
  occasion text,
  season text,
  temperature text,
  boldness text,
  rationale text,
  verdict text not null check (verdict in ('gostei', 'nao_gostei')),
  created_at timestamptz not null default now()
);

create index if not exists look_feedback_verdict_idx on look_feedback (verdict);
create index if not exists look_feedback_curated_idx on look_feedback (curated_look_id);
create index if not exists curated_looks_suppressed_idx on curated_looks (suppressed);
