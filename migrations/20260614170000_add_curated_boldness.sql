-- Migration 20260614170000_add_curated_boldness
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).

-- Eixo de OUSADIA dos looks curados, pra cliente pedir um grupo mais discreto ou
-- mais arrojado. null = sem classificação (tratado como "qualquer" no filtro).
-- discreto = neutro/clássico, calçado sóbrio | equilibrado = 1 statement + neutros |
-- ousado = cor statement, animal print, camadas e pares inesperados.
alter table curated_looks add column if not exists boldness text;
alter table curated_looks drop constraint if exists curated_looks_boldness_chk;
alter table curated_looks add constraint curated_looks_boldness_chk
  check (boldness is null or boldness in ('discreto', 'equilibrado', 'ousado'));
create index if not exists curated_looks_boldness_idx on curated_looks (occasion, boldness);
