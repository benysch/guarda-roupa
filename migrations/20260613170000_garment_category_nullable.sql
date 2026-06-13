-- Migration 20260613170000_garment_category_nullable
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Banco compartilhado por 3 apps; aplicar novas migrations só via MCP apply_migration.

-- Ingestão "só foto" (sem IA): a peça entra CRUA (status='needs_review') e a Muri
-- classifica na mão no site. Crua ainda não tem categoria, então category deixa de
-- ser obrigatória. Peças classificadas/processadas continuam preenchendo category.
alter table garments alter column category drop not null;
