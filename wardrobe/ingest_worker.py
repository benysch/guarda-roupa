"""
Worker de ingestão em segundo plano: drena a `ingest_queue`.

No modo rápido, o bot só enfileira a foto (file_id) e responde na hora. O trabalho
acontece aqui, fora da conversa. Há dois modos, controlados pela env `INGEST_USE_AI`:

- **IA LIGADA** (`INGEST_USE_AI=1`): baixa → extrai metadados com o Gemini → salva
  como `processed` (entra direto no acervo) → gera embedding. Lento (~dezenas de s
  por peça); processa POUCAS por invocação.
- **IA DESLIGADA** (padrão, por causa da quota free tier do Gemini): baixa → salva a
  peça CRUA como `needs_review` (a Muri classifica na mão no site). Rápido; processa
  um lote maior por invocação.

Disparado pelo endpoint `GET /api/process-queue`, chamado por um job pg_cron no
Supabase (~1x/min). O próximo tick pega o resto. Ao esvaziar a fila de um chat,
avisa o usuário no Telegram.
"""

import logging
import os

from . import embeddings, storage
from .config import get_settings
from .extractor import ExtractionError, extract_garment
from .imaging import ImageValidationError, normalize_image
from .telegram_bot import Telegram

logger = logging.getLogger(__name__)

# Interruptor da IA. Hoje DESLIGADO (quota free tier do Gemini estourava em 429).
# Para religar quando houver billing: setar INGEST_USE_AI=1 na Vercel — zero código.
USE_AI = os.getenv("INGEST_USE_AI", "0").lower() in ("1", "true", "yes", "on")

# Peças por invocação. Com IA, baixo (cada extração é lenta); sem IA, maior (cada
# peça é só download+upload). Cabe no orçamento de tempo do Fluid; o cron drena o resto.
BATCH = int(os.getenv("INGEST_BATCH", "1" if USE_AI else "6"))


def process_pending(limit: int = BATCH) -> dict:
    """Reivindica e processa um lote da fila; avisa chats cuja fila esvaziou."""
    settings = get_settings()
    tg = Telegram(settings.telegram_bot_token)

    jobs = storage.claim_ingest_jobs(limit)
    for job in jobs:
        _process_one(tg, job)

    for chat_id in {j["chat_id"] for j in jobs}:
        _maybe_notify(tg, chat_id)

    return {"claimed": len(jobs)}


def _process_one(tg: Telegram, job: dict) -> None:
    job_id = job["id"]
    try:
        raw = tg.download_photo(job["file_id"])
        norm = normalize_image(raw)
    except ImageValidationError:
        storage.finish_ingest(job_id, "failed", "imagem ilegível")
        return
    except Exception:
        logger.exception("falha ao baixar/normalizar o job %s", job_id)
        storage.finish_ingest(job_id, "failed", "falha ao baixar a foto")
        return

    if storage.find_existing_id(norm.content_hash):
        storage.finish_ingest(job_id, "done")  # duplicata: já está no guarda-roupa
        return

    if USE_AI:
        _process_with_ai(job_id, norm)
    else:
        _process_bare(job_id, norm)


def _process_bare(job_id: str, norm) -> None:
    """Sem IA: sobe só a foto como peça crua p/ classificação manual no site."""
    garment_id = storage.new_garment_id()
    image_path = storage.upload_image(garment_id, norm.jpeg_bytes)
    storage.insert_bare_garment(
        image_path=image_path,
        content_hash=norm.content_hash,
        garment_id=garment_id,
        status="needs_review",
    )
    storage.finish_ingest(job_id, "done")


def _process_with_ai(job_id: str, norm) -> None:
    """Com IA: extrai metadados, salva como processed e gera embedding."""
    try:
        meta = extract_garment(norm.jpeg_bytes)
    except ExtractionError as exc:
        msg = str(exc)
        if _is_transient(msg):
            # 429/quota/5xx é transitório: devolve pra fila e tenta no próximo tick
            # (quando a quota do Gemini liberar). Não queima a peça.
            logger.warning("job %s adiado (transitório): %s", job_id, msg[:160])
            storage.requeue_ingest(job_id, f"adiado: {msg}"[:480])
        else:
            logger.exception("extração falhou no job %s", job_id)
            storage.finish_ingest(job_id, "failed", f"IA: {msg}"[:480])
        return

    if not meta.is_garment:
        storage.finish_ingest(job_id, "failed", "não parecia uma peça de roupa")
        return

    garment_id = storage.new_garment_id()
    image_path = storage.upload_image(garment_id, norm.jpeg_bytes)
    storage.insert_garment(
        image_path=image_path,
        content_hash=norm.content_hash,
        meta=meta,
        garment_id=garment_id,
        status="processed",  # entra direto no acervo; ajustes ficam pro site
    )

    # embedding p/ busca semântica — não-fatal: a peça já está salva
    try:
        g0 = storage.get_garment(garment_id)
        storage.update_embedding(garment_id, embeddings.embed(embeddings.garment_text(g0)))
    except Exception:
        logger.exception("falha ao gerar embedding de %s", garment_id)

    storage.finish_ingest(job_id, "done")


# Trechos que indicam erro TRANSITÓRIO do Gemini (vale re-tentar depois).
_TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "quota", "exceeded", "503", "UNAVAILABLE", "500")


def _is_transient(msg: str) -> bool:
    return any(s in msg for s in _TRANSIENT)


def _maybe_notify(tg: Telegram, chat_id: int) -> None:
    """Quando a fila do chat esvazia, manda um resumo do lote (uma vez só)."""
    if storage.chat_has_open_jobs(chat_id):
        return  # ainda tem foto na fila desse chat; espera o lote terminar
    results = storage.unnotified_results(chat_id)
    if not results:
        return

    done = sum(1 for r in results if r["status"] == "done")
    failed = sum(1 for r in results if r["status"] == "failed")
    parts = []
    if done:
        s = "s" if done != 1 else ""
        if USE_AI:
            parts.append(f"✅ {done} peça{s} catalogada{s}")
        else:
            parts.append(f"📸 {done} foto{s} no site, pronta{s} pra classificar")
    if failed:
        s = "s" if failed != 1 else ""
        parts.append(f"⚠️ {failed} ignorada{s} (imagem ilegível)")
    tail = "_Abra a aba 'A classificar' no site e preencha._" if not USE_AI else (
        "_Revise e ajuste o que quiser no site._"
    )
    msg = " · ".join(parts) + "\n\n" + tail

    tg.send_message(chat_id, msg)
    storage.mark_notified([r["id"] for r in results])
