-- Migration 20260607174451_add_garment_identity_fields
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).

alter table garments
  add column if not exists brand      text,
  add column if not exists model_name text,
  add column if not exists material   text;

create index if not exists garments_material_idx on garments (material);
create index if not exists garments_brand_idx    on garments (brand);
