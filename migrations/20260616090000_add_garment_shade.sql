-- Tom específico que refina a família de cor (display/busca). Família segue
-- sendo primary_color (usada pelo motor de looks). null = tom indefinido.
alter table garments
  add column if not exists shade text;
