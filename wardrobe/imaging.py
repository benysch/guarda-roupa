"""
Validação e normalização de imagens antes da extração.

- Aceita JPEG/PNG/WEBP/HEIC; converte tudo para JPEG.
- Redimensiona para no máximo MAX_DIM px no maior lado (economiza tokens do
  Gemini e espaço no Storage).
- Calcula o sha256 do conteúdo NORMALIZADO -> chave de idempotência/dedupe.
"""

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

# Habilita leitura de HEIC/HEIF (fotos de iPhone), se a lib estiver instalada.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - dependência opcional
    pass

MAX_DIM = 1024
JPEG_QUALITY = 85
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


class ImageValidationError(ValueError):
    """Imagem corrompida ou em formato não suportado."""


@dataclass(frozen=True)
class NormalizedImage:
    jpeg_bytes: bytes
    content_hash: str
    mime_type: str = "image/jpeg"


def normalize_image(raw: bytes) -> NormalizedImage:
    """Decodifica, corrige orientação EXIF, redimensiona e recodifica em JPEG."""
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # respeita rotação do celular
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError(f"Não foi possível decodificar a imagem: {exc}") from exc

    img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    jpeg_bytes = buffer.getvalue()

    content_hash = hashlib.sha256(jpeg_bytes).hexdigest()
    return NormalizedImage(jpeg_bytes=jpeg_bytes, content_hash=content_hash)
