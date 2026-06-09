-- Migration 20260609015935_create_match_garments_fn
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Busca semântica: índice HNSW (cosseno) + RPC match_garments para o pgvector.

create index if not exists garments_embedding_idx
  on garments using hnsw (embedding vector_cosine_ops);

create or replace function match_garments(
  query_embedding vector(768),
  match_count int default 5
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
         1 - (g.embedding <=> query_embedding) as similarity
  from garments g
  where g.embedding is not null
    and g.status = 'processed'
  order by g.embedding <=> query_embedding
  limit match_count;
$$;
