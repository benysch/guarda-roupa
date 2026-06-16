#!/usr/bin/env python3
"""
Monta "pacotes" pra gerar a foto do look numa modelo DE GRAÇA no app do Gemini
(gemini.google.com — o nano-banana é gratuito). Para cada look curado AINDA SEM
foto (model_image nulo), cria uma pasta com:

  - as fotos das peças do look (pra você arrastar no chat);
  - prompt.txt  -> o texto pronto pra colar;
  - look_id.txt -> o id do look (o save-back usa pra cachear a imagem certa).

Fluxo:
  1) .venv/bin/python scripts/build_look_packets.py            (gera ~/look-packets/)
  2) abra cada pasta, jogue as fotos + cole o prompt no Gemini, salve a imagem
     gerada DENTRO da própria pasta como 'modelo.png';
  3) .venv/bin/python scripts/save_look_images.py             (sobe e cacheia tudo)

Idempotente: só processa looks sem foto. Reexecutar pula os já feitos.
Uso: scripts/build_look_packets.py [--out DIR] [--limit N]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wardrobe import storage, style_profile  # noqa: E402

# ordem de prioridade das ocasiões (as mais usadas primeiro)
_OCC_PRIORITY = {
    None: 0, "dia_a_dia": 1, "trabalho": 2,
    "almoco_amigas": 3, "jantar": 4, "festa": 5,
}
_BOLD_PRIORITY = {"equilibrado": 0, "discreto": 1, "ousado": 2, None: 3}


def _slug(s):
    return (s or "geral").replace("_", "-")


def _prompt(look, pieces) -> str:
    occ = (look.get("occasion") or "uso geral do dia a dia").replace("_", " ")
    temp = look.get("temperature")
    bold = look.get("boldness")
    ctx = [f"ocasião: {occ}"]
    if temp:
        ctx.append(f"clima: {temp}")
    if bold:
        ctx.append(f"pegada: {bold}")
    lista = "\n".join(
        f"  - {p.get('subcategory') or p.get('category')} {p.get('primary_color') or ''}".rstrip()
        for p in pieces
    )
    return (
        "Gere UMA fotografia editorial de moda: uma modelo vestindo TODAS as peças "
        "das fotos de referência anexadas, combinadas como um único look coerente.\n"
        f"Contexto do look — {'; '.join(ctx)}.\n\n"
        "Peças do look (todas devem aparecer vestidas):\n"
        f"{lista}\n\n"
        "Regras: corpo inteiro, pose natural de lookbook, fundo de estúdio clean e "
        "neutro, luz suave. Mantenha FIELMENTE as cores, estampas e o caimento de "
        "cada peça mostrada nas referências. Não invente peças que não estão nas fotos.\n\n"
        + style_profile.prompt_fragment()
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/look-packets"))
    ap.add_argument("--limit", type=int, default=0, help="0 = todos")
    args = ap.parse_args()

    client = storage.get_supabase_client()
    rows = (
        client.table(storage.CURATED_LOOKS)
        .select("*")
        .eq("suppressed", False)
        .is_("model_image", "null")
        .execute()
        .data
        or []
    )
    garments = {g["id"]: g for g in storage.fetch_garments()}

    rows.sort(key=lambda r: (
        _OCC_PRIORITY.get(r.get("occasion"), 9),
        0 if not r.get("temperature") else 1,
        _BOLD_PRIORITY.get(r.get("boldness"), 9),
        r.get("variant", 0),
    ))
    if args.limit:
        rows = rows[: args.limit]

    os.makedirs(args.out, exist_ok=True)
    feitos = 0
    for i, look in enumerate(rows, 1):
        pieces = [garments[g] for g in (look.get("garment_ids") or []) if g in garments]
        if not pieces:
            continue
        name = f"{i:02d}_{_slug(look.get('occasion'))}_{_slug(look.get('boldness'))}"
        if look.get("temperature"):
            name += f"_{look['temperature']}"
        folder = os.path.join(args.out, name)
        os.makedirs(folder, exist_ok=True)

        with open(os.path.join(folder, "look_id.txt"), "w") as f:
            f.write(look["id"])
        with open(os.path.join(folder, "prompt.txt"), "w") as f:
            f.write(_prompt(look, pieces))
        for n, p in enumerate(pieces, 1):
            img = storage.download_image(p["id"])
            if not img:
                continue
            fn = f"{n}_{_slug(p.get('subcategory') or p.get('category'))}_{_slug(p.get('primary_color'))}.jpg"
            with open(os.path.join(folder, fn), "wb") as f:
                f.write(img)
        feitos += 1
        print(f"  ✓ {name}  ({len(pieces)} peças)")

    print(f"\n{feitos} pacotes em {args.out}")
    print("Agora: abra cada pasta, jogue as fotos + cole o prompt.txt no app do "
          "Gemini, e salve a imagem gerada como 'modelo.png' DENTRO da pasta.")
    print("Depois rode: .venv/bin/python scripts/save_look_images.py")


if __name__ == "__main__":
    main()
