"""
Extração de metadados via Gemini 2.5 Flash (Structured Outputs).

NÚCLEO REAPROVEITÁVEL: `extract_garment(jpeg_bytes)` não conhece pasta, CLI nem
Supabase. Recebe bytes JPEG e devolve um `GarmentMetadata` validado. O script
batch (`ingest.py`) e um futuro endpoint de app chamam exatamente esta função.
"""

import logging

from google.genai import types
from google.genai.errors import APIError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import get_gemini_client, get_settings
from .schema import GarmentMetadata

logger = logging.getLogger(__name__)

_PROMPT = """Você é uma consultora de moda especialista em moda feminina.
Analise a peça de roupa, calçado ou acessório na imagem e extraia os metadados
no schema fornecido.

Regras:
- Se a imagem NÃO mostrar claramente uma peça (ex: paisagem, rosto, objeto
  aleatório), defina is_garment=false e preencha o resto com os melhores palpites
  neutros.
- Escolha sempre o valor de enum mais próximo; não invente categorias.
- Use os grupos próprios quando aplicável: meias/meia-calça -> category=hosiery;
  peças íntimas (sutiã, calcinha) -> lingerie; pijama/camisola/robe -> sleepwear;
  biquíni/maiô/saída de praia -> beachwear.
- Preencha apenas os campos condicionais (length, sleeve_length, neckline,
  heel_height) quando fizerem sentido para a categoria; deixe null caso contrário.
- brand e model_name: preencha SOMENTE se houver logo, etiqueta ou estampa de
  marca legível na imagem. NÃO adivinhe a marca pelo estilo; deixe null.
- Em `description`, escreva UMA frase natural, como descreveria a peça para uma
  cliente montar um look.
- Seja honesta em extraction_confidence: reduza se a foto estiver escura, cortada
  ou ambígua."""


class ExtractionError(RuntimeError):
    """Falha definitiva ao extrair metadados (após retries)."""


def _is_retryable(exc: BaseException) -> bool:
    """Erros transitórios da API (429/5xx/timeout) valem retry; 4xx não."""
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        return code is None or code == 429 or code >= 500
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=1, max=30),
    reraise=True,
)
def _call_gemini(jpeg_bytes: bytes) -> GarmentMetadata:
    settings = get_settings()
    client = get_gemini_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
            _PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GarmentMetadata,
            temperature=0.1,
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, GarmentMetadata):
        # Structured output raramente falha, mas se vier vazio/inválido, sinaliza.
        raise ExtractionError("Resposta do Gemini não pôde ser parseada no schema.")
    return parsed


def extract_garment(jpeg_bytes: bytes) -> GarmentMetadata:
    """Extrai metadados de uma imagem JPEG já normalizada. Lança ExtractionError."""
    try:
        return _call_gemini(jpeg_bytes)
    except APIError as exc:
        raise ExtractionError(f"Erro da API Gemini: {exc}") from exc
