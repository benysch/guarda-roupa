-- Guarda-Roupa Inteligente — tabela de peças (fase de ingestão).
-- Estratégia híbrida: colunas promovidas indexadas (filtro de composição) +
-- attributes jsonb (dump completo do Pydantic) + imagem no Storage.

create extension if not exists vector;

create table if not exists garments (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid,                       -- nullable: single-user agora, multiusuário depois
  created_at            timestamptz default now(),
  -- imagem
  image_path            text not null,              -- caminho no bucket -> signed URL
  content_hash          text unique,                -- sha256 do JPEG normalizado -> dedupe/idempotência
  -- colunas promovidas (filtráveis)
  category              text not null,
  subcategory           text,
  primary_color         text,
  pattern               text,
  formality             text,
  length                text,
  seasons               text[] default '{}',
  style_aesthetics      text[] default '{}',
  occasions             text[] default '{}',
  -- flexível + busca
  attributes            jsonb not null,             -- GarmentMetadata.model_dump()
  description           text,
  embedding             vector(768),                -- criada agora, populada depois
  status                text default 'processed',   -- processed | failed | needs_review
  extraction_confidence numeric
);

create index if not exists garments_category_formality_idx on garments (category, formality);
create index if not exists garments_primary_color_idx       on garments (primary_color);
create index if not exists garments_seasons_idx             on garments using gin (seasons);
create index if not exists garments_occasions_idx           on garments using gin (occasions);
create index if not exists garments_aesthetics_idx          on garments using gin (style_aesthetics);
create index if not exists garments_attributes_idx          on garments using gin (attributes);

-- Bucket privado para as fotos (acesso via signed URL).
insert into storage.buckets (id, name, public)
values ('wardrobe', 'wardrobe', false)
on conflict (id) do nothing;
