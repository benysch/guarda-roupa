"""
Persistência no Supabase: dedupe, upload no Storage e insert no Postgres.

Espelha a estratégia híbrida do schema: colunas promovidas (filtráveis) +
`attributes` jsonb com o dump Pydantic completo + imagem no bucket privado.
"""

import logging
import uuid
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .config import get_settings, get_supabase_client
from .schema import GarmentMetadata

logger = logging.getLogger(__name__)

TABLE = "garments"


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
