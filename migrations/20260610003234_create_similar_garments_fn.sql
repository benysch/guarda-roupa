-- Migration 20260610003234_create_similar_garments_fn
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- "Peças parecidas com esta": vizinhos por embedding, excluindo a própria peça.

create or replace function similar_garments(
  source_id uuid,
  match_count int default 6
)
returns table (
  id uuid,
  category text,
  subcategory text,
  primary_color text,
  brand text,
  description text,
  image_path text,
  similarity float
)
language sql
stable
set search_path = public, extensions
as $$
  select g.id, g.category, g.subcategory, g.primary_color, g.brand,
         g.description, g.image_path,
         1 - (g.embedding <=> s.embedding) as similarity
  from garments g
  cross join (select embedding from garments where id = source_id) s
  where g.id <> source_id
    and g.embedding is not null
    and s.embedding is not null
    and g.status = 'processed'
  order by g.embedding <=> s.embedding
  limit match_count;
$$;
