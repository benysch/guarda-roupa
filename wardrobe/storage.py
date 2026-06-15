"""
Persistência no Supabase: dedupe, upload no Storage e insert no Postgres.

Espelha a estratégia híbrida do schema: colunas promovidas (filtráveis) +
`attributes` jsonb com o dump Pydantic completo + imagem no bucket privado.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .config import get_settings, get_supabase_client
from .schema import GarmentMetadata

logger = logging.getLogger(__name__)

TABLE = "garments"
QUEUE = "ingest_queue"
PREFS = "telegram_prefs"


def find_existing_id(content_hash: str) -> Optional[str]:
    """Retorna o id do garment com este hash, se já existir (idempotência)."""
    client = get_supabase_client()
    resp = (
        client.table(TABLE)
        .select("id")
        .eq("content_hash", content_hash)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["id"]
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15), reraise=True)
def upload_image(garment_id: str, jpeg_bytes: bytes) -> str:
    """Faz upload no bucket privado e devolve o image_path (caminho do objeto)."""
    settings = get_settings()
    client = get_supabase_client()
    path = f"{garment_id}.jpg"
    client.storage.from_(settings.supabase_bucket).upload(
        path,
        jpeg_bytes,
        {"content-type": "image/jpeg", "upsert": "true"},
    )
    return path


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15), reraise=True)
def upload_cutout(garment_id: str, png_bytes: bytes) -> str:
    """Sobe a imagem recortada (fundo transparente) em '{id}_cutout.png' e devolve o path."""
    settings = get_settings()
    client = get_supabase_client()
    path = f"{garment_id}_cutout.png"
    client.storage.from_(settings.supabase_bucket).upload(
        path,
        png_bytes,
        {"content-type": "image/png", "upsert": "true"},
    )
    return path


def _row_from_metadata(
    garment_id: str,
    image_path: str,
    content_hash: str,
    meta: GarmentMetadata,
    status: str,
) -> dict:
    """Monta a linha: colunas promovidas + attributes jsonb completo."""
    return {
        "id": garment_id,
        "image_path": image_path,
        "content_hash": content_hash,
        "category": meta.category.value,
        "subcategory": meta.subcategory.value,
        "primary_color": meta.primary_color.value,
        "pattern": meta.pattern.value,
        "material": meta.material.value if meta.material else None,
        "formality": meta.formality.value,
        "length": meta.length.value if meta.length else None,
        "brand": meta.brand,
        "model_name": meta.model_name,
        "seasons": [s.value for s in meta.seasons],
        "style_aesthetics": [s.value for s in meta.style_aesthetics],
        "occasions": [o.value for o in meta.occasions],
        "attributes": meta.model_dump(mode="json"),
        "description": meta.description,
        "status": status,
        "extraction_confidence": meta.extraction_confidence,
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15), reraise=True)
def insert_garment(
    image_path: str,
    content_hash: str,
    meta: GarmentMetadata,
    garment_id: str,
    status: str = "processed",
) -> str:
    """Insere a peça e devolve o id."""
    client = get_supabase_client()
    row = _row_from_metadata(garment_id, image_path, content_hash, meta, status)
    client.table(TABLE).insert(row).execute()
    return garment_id


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15), reraise=True)
def insert_bare_garment(
    image_path: str,
    content_hash: str,
    garment_id: str,
    status: str = "needs_review",
) -> str:
    """Insere uma peça CRUA (sem IA): só a foto. A Muri classifica na mão no site."""
    client = get_supabase_client()
    client.table(TABLE).insert(
        {
            "id": garment_id,
            "image_path": image_path,
            "content_hash": content_hash,
            "attributes": {},
            "status": status,
        }
    ).execute()
    return garment_id


def new_garment_id() -> str:
    return str(uuid.uuid4())


def get_garment(garment_id: str) -> Optional[dict]:
    """Lê uma peça pelo id (ou None)."""
    client = get_supabase_client()
    resp = client.table(TABLE).select("*").eq("id", garment_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def update_garment(garment_id: str, fields: dict) -> None:
    """Atualiza campos de uma peça (ex: brand, model_name, category)."""
    client = get_supabase_client()
    client.table(TABLE).update(fields).eq("id", garment_id).execute()


def fetch_garments(statuses: tuple[str, ...] = ("processed",)) -> list[dict]:
    """Lê o acervo (por padrão só peças já processadas) para a composição de looks."""
    client = get_supabase_client()
    resp = client.table(TABLE).select("*").in_("status", list(statuses)).execute()
    return resp.data or []


def _vector_literal(embedding: list[float]) -> str:
    """Formato textual aceito pelo pgvector via PostgREST: '[1,2,3]'."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def update_embedding(garment_id: str, embedding: list[float]) -> None:
    """Grava o vetor de busca semântica de uma peça."""
    client = get_supabase_client()
    client.table(TABLE).update({"embedding": _vector_literal(embedding)}).eq(
        "id", garment_id
    ).execute()


def match_garments(embedding: list[float], match_count: int = 5) -> list[dict]:
    """Busca semântica: peças mais próximas do vetor de consulta (via RPC pgvector)."""
    client = get_supabase_client()
    resp = client.rpc(
        "match_garments",
        {"query_embedding": _vector_literal(embedding), "match_count": match_count},
    ).execute()
    return resp.data or []


def similar_garments(garment_id: str, match_count: int = 6) -> list[dict]:
    """Peças mais próximas de uma peça (vizinhos por embedding, exclui a própria)."""
    client = get_supabase_client()
    resp = client.rpc(
        "similar_garments", {"source_id": garment_id, "match_count": match_count}
    ).execute()
    return resp.data or []


def download_image(garment_id: str) -> Optional[bytes]:
    """Baixa os bytes JPEG de uma peça do bucket privado (para o estilista visual)."""
    settings = get_settings()
    client = get_supabase_client()
    try:
        return client.storage.from_(settings.supabase_bucket).download(f"{garment_id}.jpg")
    except Exception:
        logger.warning("falha ao baixar imagem de %s", garment_id)
        return None


def signed_url(image_path: str, expires_in: int = 600) -> Optional[str]:
    """URL assinada temporária de uma imagem do bucket privado (o Telegram busca por ela)."""
    settings = get_settings()
    client = get_supabase_client()
    try:
        resp = client.storage.from_(settings.supabase_bucket).create_signed_url(
            image_path, expires_in
        )
    except Exception:  # imagem ausente / falha no Storage não deve derrubar o look
        logger.exception("falha ao assinar URL de %s", image_path)
        return None
    if isinstance(resp, dict):
        return resp.get("signedURL") or resp.get("signedUrl")
    return None


# --------------------------------------------------------------------------- #
# Modo rápido / fila de ingestão em segundo plano
# --------------------------------------------------------------------------- #
def get_fast_mode(chat_id: int) -> bool:
    """O chat está em modo rápido (só mandar fotos, processa em background)?"""
    client = get_supabase_client()
    resp = (
        client.table(PREFS).select("fast_mode").eq("chat_id", chat_id).limit(1).execute()
    )
    return bool(resp.data[0]["fast_mode"]) if resp.data else False


def set_fast_mode(chat_id: int, fast: bool) -> None:
    """Liga/desliga o modo rápido de um chat."""
    client = get_supabase_client()
    client.table(PREFS).upsert(
        {"chat_id": chat_id, "fast_mode": fast, "updated_at": _now_iso()}
    ).execute()


def enqueue_ingest(chat_id: int, file_id: str) -> None:
    """Enfileira uma foto para catalogação em segundo plano."""
    client = get_supabase_client()
    client.table(QUEUE).insert({"chat_id": chat_id, "file_id": file_id}).execute()


def claim_ingest_jobs(limit: int) -> list[dict]:
    """Reivindica até `limit` jobs pendentes (atômico; reaproveita travados)."""
    client = get_supabase_client()
    resp = client.rpc("claim_ingest_jobs", {"n": limit}).execute()
    return resp.data or []


def finish_ingest(job_id: str, status: str, error: Optional[str] = None) -> None:
    """Marca um job como 'done' ou 'failed'."""
    client = get_supabase_client()
    client.table(QUEUE).update(
        {"status": status, "error": error, "processed_at": _now_iso()}
    ).eq("id", job_id).execute()


def requeue_ingest(job_id: str, note: Optional[str] = None) -> None:
    """Devolve um job pra fila (erro transitório): volta a 'pending' p/ re-tentar."""
    client = get_supabase_client()
    client.table(QUEUE).update(
        {"status": "pending", "started_at": None, "processed_at": None, "error": note}
    ).eq("id", job_id).execute()


def chat_has_open_jobs(chat_id: int) -> bool:
    """Ainda há fotos pendentes/em processamento na fila deste chat?"""
    client = get_supabase_client()
    resp = (
        client.table(QUEUE)
        .select("id")
        .eq("chat_id", chat_id)
        .in_("status", ["pending", "processing"])
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def unnotified_results(chat_id: int) -> list[dict]:
    """Resultados (done/failed) deste chat que ainda não foram avisados."""
    client = get_supabase_client()
    resp = (
        client.table(QUEUE)
        .select("id,status")
        .eq("chat_id", chat_id)
        .eq("notified", False)
        .in_("status", ["done", "failed"])
        .execute()
    )
    return resp.data or []


def mark_notified(job_ids: list[str]) -> None:
    """Marca jobs como já avisados (evita avisar duas vezes)."""
    if not job_ids:
        return
    client = get_supabase_client()
    client.table(QUEUE).update({"notified": True}).in_("id", job_ids).execute()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Curadoria pré-computada (looks/mala) — o site/bot leem daqui em vez de gerar IA
# em tempo real. O Claude gera offline e grava; combo sem curadoria cai na regra.
# --------------------------------------------------------------------------- #
CURATED_LOOKS = "curated_looks"
CURATED_CAPSULES = "curated_capsules"
REQUESTS = "look_requests"


def _combo_eq(q, col: str, val):
    """Filtro de combo: igualdade quando há valor, IS NULL quando ausente."""
    return q.eq(col, val) if val else q.is_(col, "null")


def get_curated_looks(occasion, season, temperature, boldness=None) -> list[dict]:
    """Looks curados (variações) para um combo exato; filtra por ousadia se informada."""
    client = get_supabase_client()
    q = client.table(CURATED_LOOKS).select("*").eq("suppressed", False)
    q = _combo_eq(q, "occasion", occasion)
    q = _combo_eq(q, "season", season)
    q = _combo_eq(q, "temperature", temperature)
    if boldness:
        q = q.eq("boldness", boldness)
    return q.execute().data or []


def get_curated_capsule(days: int, occasion, night, season, temperature) -> list[dict]:
    """Cápsulas curadas para um combo exato de viagem."""
    client = get_supabase_client()
    q = client.table(CURATED_CAPSULES).select("*").eq("days", days)
    q = _combo_eq(q, "occasion", occasion)
    q = _combo_eq(q, "night", night)
    q = _combo_eq(q, "season", season)
    q = _combo_eq(q, "temperature", temperature)
    return q.execute().data or []


def log_request(kind: str, combo: str) -> None:
    """Registra um combo pedido sem cache (best-effort; prioriza o que gerar depois)."""
    try:
        client = get_supabase_client()
        client.table(REQUESTS).upsert(
            {"kind": kind, "combo": combo, "last_requested": _now_iso()},
            on_conflict="kind,combo",
        ).execute()
    except Exception:
        logger.debug("log_request falhou (não-fatal)", exc_info=True)
