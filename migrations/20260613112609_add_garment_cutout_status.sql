-- Migration 20260613112609_add_garment_cutout_status
-- Espelho fiel do SQL aplicado (fonte da verdade: histórico do Supabase).
-- Banco compartilhado por 3 apps; aplicar novas migrations só via MCP apply_migration.

-- Recorte de fundo (background removal) das fotos do guarda-roupa.
-- cutout_status: null = não gerado | 'pending' = recorte gerado, aguardando revisão
--                'approved' = usar o recorte no site | 'rejected' = descartado, manter original
-- O recorte é gravado no Storage por convenção em '{id}_cutout.png'.
alter table garments add column if not exists cutout_status text;

alter table garments drop constraint if exists garments_cutout_status_chk;
alter table garments add constraint garments_cutout_status_chk
  check (cutout_status is null or cutout_status in ('pending', 'approved', 'rejected'));
