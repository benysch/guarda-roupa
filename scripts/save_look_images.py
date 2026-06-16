#!/usr/bin/env python3
"""
Sobe as fotos da modelo geradas no app do Gemini e as cacheia nos looks.

Varre as pastas de pacotes (ver build_look_packets.py). Para cada pasta que tem
'look_id.txt' E uma imagem gerada chamada 'modelo.(png|jpg|jpeg|webp)', converte
pra PNG, sobe no bucket como 'look_<id>.png' e seta curated_looks.model_image.
O site passa a mostrar a foto na hora (sem API, sem custo).

Idempotente: reprocessa só pastas com 'modelo.*'. Apague/renomeie pra refazer.
Uso: scripts/save_look_images.py [--dir DIR] [--look-id ID --image PATH]
"""

import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from wardrobe import storage  # noqa: E402

_MODELO_NAMES = ("modelo.png", "modelo.jpg", "modelo.jpeg", "modelo.webp")


def _upload(look_id: str, image_path: str) -> None:
    png = io.BytesIO()
    Image.open(image_path).convert("RGB").save(png, format="PNG")
    key = f"look_{look_id}.png"
    client = storage.get_supabase_client()
    bucket = storage.get_settings().supabase_bucket
    client.storage.from_(bucket).upload(
        key, png.getvalue(), {"content-type": "image/png", "upsert": "true"}
    )
    client.table(storage.CURATED_LOOKS).update({"model_image": key}).eq(
        "id", look_id
    ).execute()
    print(f"  ✓ {look_id} -> {key}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/look-packets"))
    ap.add_argument("--look-id", help="modo avulso: id do look")
    ap.add_argument("--image", help="modo avulso: caminho da imagem")
    args = ap.parse_args()

    if args.look_id and args.image:
        _upload(args.look_id, args.image)
        return

    n = 0
    for entry in sorted(os.listdir(args.dir)):
        folder = os.path.join(args.dir, entry)
        idf = os.path.join(folder, "look_id.txt")
        if not os.path.isdir(folder) or not os.path.exists(idf):
            continue
        modelo = next(
            (os.path.join(folder, m) for m in _MODELO_NAMES
             if os.path.exists(os.path.join(folder, m))),
            None,
        )
        if not modelo:
            continue
        with open(idf) as f:
            look_id = f.read().strip()
        _upload(look_id, modelo)
        n += 1

    print(f"\n{n} fotos cacheadas." if n else
          "Nenhuma 'modelo.*' encontrada nas pastas. Gere as imagens primeiro.")


if __name__ == "__main__":
    main()
