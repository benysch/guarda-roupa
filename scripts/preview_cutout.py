#!/usr/bin/env python3
"""
PROTÓTIPO de recorte de fundo — só pra avaliar QUALIDADE antes de comprometer.

NÃO faz parte do pipeline nem entra no bundle da Vercel. Roda local, num venv
ISOLADO com rembg (o .venv do projeto fica limpo). Usa o modelo `u2net_cloth_seg`
(segmentação de vestuário) — o `u2net` genérico falha feio em roupa (trata o
tecido como fundo e mantém só a estampa de alto contraste).

Quirk do cloth_seg: a saída vem com 3x a altura (faixas corpo superior/inferior/
inteiro empilhadas). Aqui recortamos no bounding box do conteúdo opaco, então o
resultado fica enquadrado na peça.

Pré-requisito (uma vez):
    uv venv --python 3.14 ~/.cache/guarda-roupa-cutout/venv
    uv pip install --python ~/.cache/guarda-roupa-cutout/venv/bin/python "rembg[cpu]" pillow

Uso (NUMBA_DISABLE_JIT=1 evita o crash do llvmlite em aarch64/WSL2):
    NUMBA_DISABLE_JIT=1 ~/.cache/guarda-roupa-cutout/venv/bin/python \
        scripts/preview_cutout.py ./fotos_teste --out /tmp/cutout_test
"""

import argparse
import io
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps
from rembg import new_session, remove

SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
EDITORIAL_BG = (245, 243, 240, 255)  # off-white da paleta inverno frio
PADDING = 0.04  # margem ao redor da peça, fração do lado


def load_rgb(path: Path) -> Image.Image:
    """Decodifica respeitando a orientação EXIF (igual ao normalize_image)."""
    img = Image.open(io.BytesIO(path.read_bytes()))
    return ImageOps.exif_transpose(img).convert("RGB")


def crop_to_content(cut: Image.Image) -> Image.Image | None:
    """Isola a peça desfazendo as 3 faixas (superior/inferior/inteiro) do cloth_seg.

    O cloth_seg empilha 3 máscaras verticalmente e pode marcar a mesma peça em mais
    de uma faixa. Dividimos nas 3, escolhemos a de MAIOR área opaca e recortamos no
    bounding box dela. Devolve None se não sobrou peça (foto não-roupa)."""
    w, h = cut.size
    band_h = h // 3
    mask = cut.getchannel("A").point(lambda a: 255 if a > 10 else 0)

    best_band, best_area = None, 0
    for i in range(3):
        top = i * band_h
        bottom = h if i == 2 else top + band_h
        band = cut.crop((0, top, w, bottom))
        area = sum(band.getchannel("A").point(lambda a: 1 if a > 10 else 0).getdata())
        if area > best_area:
            best_area, best_band = area, band
    if best_band is None or best_area == 0:
        return None

    bbox = best_band.getchannel("A").point(lambda a: 255 if a > 10 else 0).getbbox()
    if bbox is None:
        return None
    pad = int(PADDING * max(best_band.size))
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(best_band.size[0], bbox[2] + pad)
    bottom = min(best_band.size[1], bbox[3] + pad)
    return best_band.crop((left, top, right, bottom))


def on_background(cut: Image.Image, color=EDITORIAL_BG) -> Image.Image:
    bg = Image.new("RGBA", cut.size, color)
    bg.alpha_composite(cut)
    return bg.convert("RGB")


def main() -> int:
    ap = argparse.ArgumentParser(description="Preview de recorte de fundo (qualidade)")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--out", type=Path, default=Path("/tmp/cutout_test"))
    ap.add_argument("--model", default="u2net_cloth_seg")
    args = ap.parse_args()

    if not args.folder.is_dir():
        print(f"pasta não encontrada: {args.folder}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    images = sorted(p for p in args.folder.rglob("*") if p.suffix.lower() in SUFFIXES)
    if not images:
        print("nenhuma imagem suportada", file=sys.stderr)
        return 0

    t = time.time()
    session = new_session(args.model)
    print(f"modelo {args.model} carregado em {time.time() - t:.1f}s\n")

    for path in images:
        img = load_rgb(path)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)

        t = time.time()
        out = remove(buf.getvalue(), session=session, post_process_mask=True)
        dt = time.time() - t

        cut = Image.open(io.BytesIO(out)).convert("RGBA")
        cropped = crop_to_content(cut)
        if cropped is None:
            print(f"{path.name}: {dt:.1f}s  SEM PEÇA (não-roupa?) — pulado")
            continue

        stem = path.stem
        cropped.save(args.out / f"{stem}_cutout.png")           # transparente
        on_background(cropped).save(args.out / f"{stem}_onbg.jpg", quality=90)  # editorial
        print(f"{path.name}: {dt:.1f}s  peça {cropped.size}")

    print(f"\nArquivos em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
