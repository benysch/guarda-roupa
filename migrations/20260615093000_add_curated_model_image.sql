-- Imagem da modelo vestindo o look (gerada no app gratuito do Gemini e cacheada).
-- Guarda a chave do objeto no bucket (ex.: 'look_<id>.png'); null = ainda sem foto.
alter table curated_looks
  add column if not exists model_image text;
