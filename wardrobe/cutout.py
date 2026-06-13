"""
Recorte de fundo (background removal) das fotos de peças.

⚠️ LOCAL-ONLY. Depende de `rembg` (extra `cutout` do pyproject) — pesado e incompatível
com o bundle serverless da Vercel. Este módulo NUNCA é importado pelo caminho do bot
(`api.telegram`); só pelo `scripts/backfill_cutouts.py`. O `import rembg` é lazy (dentro
da função) e ainda precisa de `NUMBA_DISABLE_JIT=1` — em aarch64/WSL2 o llvmlite (via
pymatting) aborta o processo no import; setamos a env antes de importar.

Modelo: `u2net_cloth_seg` (segmentação de vestuário). O `u2net` genérico é inútil para
roupa (mantém só estampas de alto contraste e descarta o tecido). Quirk do cloth_seg: a
saída tem 3x a altura (faixas corpo superior/inferior/inteiro empilhadas) e a peça pode
cair em mais de uma faixa — escolhemos a faixa de maior área opaca e recortamos no bbox.

Funciona bem em peça que contrasta com o fundo; falha em baixo contraste (branco sobre
branco) e em itens não-vestíveis (bag/accessory) — por isso o gating de categoria e a
revisão manual no site.
"""

import io
import os

# DEVE vir antes de qualquer import do rembg (que puxa numba/llvmlite): em aarch64/WSL2
# o JIT do LLVM aborta o processo no import. Sem alpha matting não usamos numba de fato,
# então desligar o JIT não custa qualidade. setdefault: respeita override do ambiente.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

from PIL import Image, ImageOps

# Categorias que valem o recorte. bag/accessory NÃO entram: o cloth_seg só segmenta
# roupa vestível e falha em bolsa/acessório.
CUTOUT_CATEGORIES = frozenset({"top", "outerwear", "hosiery", "full_body"})

_MODEL = "u2net_cloth_seg"
_PADDING = 0.04  # margem ao redor da peça, fração do maior lado
_ALPHA_FLOOR = 10  # pixel considerado "peça" se alpha > isto

_session = None  # cache do modelo (carregar é caro)


def should_cutout(category: str | None) -> bool:
    """True se a categoria vale recorte (gating — nunca bag/accessory)."""
    return category in CUTOUT_CATEGORIES


def _get_session():
    global _session
    if _session is None:
        # numba/llvmlite aborta o processo no import em aarch64; sem alpha matting
        # não perdemos qualidade desligando o JIT.
        os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
        from rembg import new_session

        _session = new_session(_MODEL)
    return _session


def _best_band(cut: Image.Image) -> Image.Image | None:
    """Desfaz as 3 faixas do cloth_seg: devolve a faixa de maior área opaca."""
    w, h = cut.size
    band_h = h // 3
    best_band, best_area = None, 0
    for i in range(3):
        top = i * band_h
        bottom = h if i == 2 else top + band_h
        band = cut.crop((0, top, w, bottom))
        mask = band.getchannel("A").point(lambda a: 1 if a > _ALPHA_FLOOR else 0)
        area = sum(mask.getdata())
        if area > best_area:
            best_area, best_band = area, band
    return best_band if best_area > 0 else None


def _crop_to_content(band: Image.Image) -> Image.Image | None:
    """Recorta no bounding box do alpha, com uma margem."""
    bbox = band.getchannel("A").point(lambda a: 255 if a > _ALPHA_FLOOR else 0).getbbox()
    if bbox is None:
        return None
    pad = int(_PADDING * max(band.size))
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(band.size[0], bbox[2] + pad)
    bottom = min(band.size[1], bbox[3] + pad)
    return band.crop((left, top, right, bottom))


def cutout_garment(jpeg_bytes: bytes) -> bytes | None:
    """Recorta a peça e devolve um PNG RGBA (fundo transparente), enquadrado na peça.

    Devolve None se o modelo não encontrou peça (ex.: foto não-roupa, baixo contraste
    extremo). Não levanta para o chamador tratar como 'mantém original' — exceções de
    runtime do rembg sobem normalmente para o backfill registrar a falha do item."""
    from rembg import remove

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(jpeg_bytes))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)

    out = remove(buf.getvalue(), session=_get_session(), post_process_mask=True)
    cut = Image.open(io.BytesIO(out)).convert("RGBA")

    band = _best_band(cut)
    if band is None:
        return None
    cropped = _crop_to_content(band)
    if cropped is None:
        return None

    result = io.BytesIO()
    cropped.save(result, "PNG", optimize=True)
    return result.getvalue()
