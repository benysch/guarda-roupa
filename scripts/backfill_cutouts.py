#!/usr/bin/env python3
"""
Backfill de recortes de fundo no acervo. LOCAL-ONLY (usa rembg — ver wardrobe/cutout.py).

Para cada peça SEM recorte (cutout_status nulo) e de categoria elegível (top/outerwear/
hosiery; nunca bag/accessory), baixa a imagem original, recorta e:
  - se o modelo achou a peça: sobe '{id}_cutout.png' e marca cutout_status='pending'
    (aguardando você aprovar no site, em /peca/{id});
  - se não achou: marca 'rejected' (não tenta de novo a cada run — é idempotente).

NÃO apaga nem altera a imagem original. Reexecutar só processa quem ainda está nulo.

Uso (NUMBA_DISABLE_JIT é setado pelo módulo, mas deixe explícito por garantia):
    NUMBA_DISABLE_JIT=1 .venv/bin/python scripts/backfill_cutouts.py [--limit N] [--dry-run]

Pré-requisito local: uv pip install -e '.[cutout]'
"""

import argparse
import logging
import os
import sys

# garante que o pacote `wardrobe` (na raiz do repo) seja importável de qualquer CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wardrobe import cutout, storage  # noqa: E402
from wardrobe.config import get_settings, get_supabase_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("backfill_cutouts")


def _candidates(limit: int | None) -> list[dict]:
    """Peças ainda sem recorte (cutout_status nulo), só categorias elegíveis."""
    client = get_supabase_client()
    q = (
        client.table("garments")
        .select("id,category,subcategory")
        .is_("cutout_status", "null")
        .in_("category", list(cutout.CUTOUT_CATEGORIES))
    )
    if limit:
        q = q.limit(limit)
    return q.execute().data or []


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill de recortes de fundo")
    ap.add_argument("--limit", type=int, default=None, help="processa no máx N peças")
    ap.add_argument("--dry-run", action="store_true", help="não grava nada, só relata")
    args = ap.parse_args()

    get_settings()  # falha cedo se faltar env
    rows = _candidates(args.limit)
    if not rows:
        logger.info("nada a fazer — nenhuma peça elegível sem recorte.")
        return 0

    logger.info("%d peça(s) elegível(is) sem recorte%s", len(rows),
                " [dry-run]" if args.dry_run else "")

    done = pending = rejected = failed = 0
    for r in rows:
        gid, cat = r["id"], r["category"]
        label = f"{cat}/{r.get('subcategory')}"
        raw = storage.download_image(gid)
        if not raw:
            logger.warning("[falha] %s %s: sem imagem original", gid[:8], label)
            failed += 1
            continue
        try:
            png = cutout.cutout_garment(raw)
        except Exception as exc:  # erro de runtime do rembg — não derruba o lote
            logger.warning("[falha] %s %s: %s", gid[:8], label, exc)
            failed += 1
            continue

        status = "pending" if png else "rejected"
        if args.dry_run:
            logger.info("[dry] %s %s -> %s", gid[:8], label, status)
        else:
            if png:
                storage.upload_cutout(gid, png)
            storage.update_garment(gid, {"cutout_status": status})
            logger.info("[%s] %s %s", status, gid[:8], label)
        done += 1
        pending += status == "pending"
        rejected += status == "rejected"

    logger.info("fim: %d processadas (%d pending, %d rejected), %d falhas",
                done, pending, rejected, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
