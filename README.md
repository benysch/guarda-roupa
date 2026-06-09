# Guarda-Roupa Inteligente — Ingestão

Transforma fotos de peças de roupa em metadados estruturados (Gemini 2.5 Flash) e
persiste no Supabase (Postgres + Storage). Esta é a **fase de ingestão**.

## Arquitetura

```
fotos/  ──►  imaging (Pillow + sha256)  ──►  dedupe  ──►  extractor (Gemini)
                                                              │
                                              upload (Storage) ◄┘
                                                      │
                                              insert (Postgres)
```

- `wardrobe/schema.py` — Enums + `GarmentMetadata` (fonte da verdade do vocabulário).
- `wardrobe/extractor.py` — **núcleo reaproveitável**: `extract_garment(jpeg_bytes)`.
  Não conhece pasta nem CLI; um futuro endpoint de app chama a mesma função.
- `wardrobe/imaging.py` — normaliza (HEIC/PNG→JPEG, ≤1024px) e calcula o hash.
- `wardrobe/storage.py` — dedupe, upload e insert (colunas promovidas + `attributes` jsonb).
- `ingest.py` — CLI batch da carga inicial, com relatório JSON e reruns idempotentes.

## Setup

```bash
uv venv && uv pip install -e .       # ou: uv pip install google-genai supabase pydantic pillow pillow-heif python-dotenv tenacity
cp .env.example .env                 # preencha GEMINI_API_KEY e as chaves do Supabase
```

### Migrations

> **Fonte da verdade = histórico do Supabase** (`supabase_migrations.schema_migrations`).
> O banco é **compartilhado** por 3 apps (`fc_*`, `pe_*`, guarda-roupa), então o
> histórico global mistura migrations de todos — um fluxo de `supabase db push`
> por-repositório não se aplica aqui.
>
> Os arquivos em `migrations/` são **espelhos fiéis** do SQL já aplicado (1 arquivo
> por versão registrada), para referência e setup de um banco do zero. **Não**
> numere migrations à mão: novas migrations só via MCP `apply_migration`, e depois
> espelhe o arquivo aqui com o nome da versão gerada.

```
migrations/20260607143505_create_garments_table.sql        # garments + índices + bucket 'wardrobe'
migrations/20260607174451_add_garment_identity_fields.sql  # brand / model_name / material
migrations/20260607224842_create_telegram_sessions.sql     # estado do bot conversacional
```

## Uso

```bash
.venv/bin/python ingest.py ./fotos_teste --workers 4
```

Gera `relatorio_ingestao.json` com o resumo (processed / skipped_duplicate /
skipped_not_garment / needs_review / failed). Rodar de novo na mesma pasta = tudo
skip (idempotência via `content_hash`).

## Verificação end-to-end

1. Aplicar a migration; confirmar tabela `garments`, extensão `vector` e bucket `wardrobe`.
2. Rodar com 3–5 fotos variadas (1 vestido, 1 sapato, 1 não-roupa para testar o guard-rail).
3. Conferir rows com colunas promovidas + `attributes` coerentes; foto não-roupa pulada;
   imagens no bucket.
4. Reexecutar → tudo skip.

## Bot do Telegram (ingestão conversacional, Vercel)

Em vez de copiar fotos para uma pasta, a Beny manda a foto no Telegram. O bot
(webhook serverless Python na Vercel) processa com a IA, salva a peça e puxa uma
conversa para confirmar a categoria e capturar marca/modelo.

- `api/telegram.py` — webhook (Vercel `BaseHTTPRequestHandler`, processa inline;
  Fluid Compute + `maxDuration: 60` no `vercel.json`).
- `wardrobe/telegram_bot.py` — cliente Telegram (httpx) + máquina de estados;
  reaproveita `imaging`/`extractor`/`storage`.
- Estado da conversa em `telegram_sessions` (serverless é stateless).
- Segurança: whitelist `TELEGRAM_ALLOWED_IDS` + segredo do webhook.

Deploy:
1. Crie o bot no @BotFather → `TELEGRAM_BOT_TOKEN`.
2. Pegue os IDs numéricos (você + Beny) no @userinfobot → `TELEGRAM_ALLOWED_IDS`.
3. Defina as envs na Vercel (GEMINI/SUPABASE + TELEGRAM_*).
4. Deploy na Vercel.
5. `python scripts/set_webhook.py https://SEU-PROJETO.vercel.app/api/telegram`

## Decisões

- Single-user (sem RLS); `user_id` nullable para futura migração multiusuário.
- `embedding vector(768)` criada agora, populada numa fase futura (busca semântica).
- Enums validados no Pydantic; colunas `text` no Postgres (flexível para evoluir).
- Ingestão por Telegram (Vercel webhook), reusando o núcleo Python; sem long-polling
  (não precisa de máquina sempre ligada).
