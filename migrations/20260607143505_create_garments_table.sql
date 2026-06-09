-- Migration 20260607143505_create_garments_table
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Banco compartilhado por 3 apps; aplicar novas migrations só via MCP apply_migration.

create extension if not exists vector;

create table if not exists garments (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid,
  created_at            timestamptz default now(),
  image_path            text not null,
  content_hash          text unique,
  category              text not null,
  subcategory           text,
  primary_color         text,
  pattern               text,
  formality             text,
  length                text,
  seasons               text[] default '{}',
  style_aesthetics      text[] default '{}',
  occasions             text[] default '{}',
  attributes            jsonb not null,
  description           text,
  embedding             vector(768),
  status                text default 'processed',
  extraction_confidence numeric
);

create index if not exists garments_category_formality_idx on garments (category, formality);
create index if not exists garments_primary_color_idx       on garments (primary_color);
create index if not exists garments_seasons_idx             on garments using gin (seasons);
create index if not exists garments_occasions_idx           on garments using gin (occasions);
create index if not exists garments_aesthetics_idx          on garments using gin (style_aesthetics);
create index if not exists garments_attributes_idx          on garments using gin (attributes);

insert into storage.buckets (id, name, public)
values ('wardrobe', 'wardrobe', false)
on conflict (id) do nothing;
