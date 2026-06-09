#!/usr/bin/env python3
"""
Popula a coluna `embedding` das peças que ainda não têm vetor.

Idempotente: só processa rows com embedding NULL. Reexecutar é seguro.

Uso:
    .venv/bin/python scripts/backfill_embeddings.py
"""

import logging
import os
import sys

# garante que o pacote `wardrobe` (na raiz do repo) seja importável de qualquer CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wardrobe import embeddings, storage  # noqa: E402
from wardrobe.config import get_supabase_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("backfill")


def main() -> int:
    client = get_supabase_client()
    rows = (
        client.table("garments").select("*").is_("embedding", "null").execute().data or []
    )
    logger.info("%d peça(s) sem embedding", len(rows))

    ok = fail = 0
    for g in rows:
        try:
            vec = embeddings.embed(embeddings.garment_text(g))
            storage.update_embedding(g["id"], vec)
            ok += 1
            logger.info("✓ %s  %s/%s", g["id"][:8], g.get("category"), g.get("primary_color"))
        except Exception as exc:
            fail += 1
            logger.warning("✗ %s  %s", g["id"][:8], exc)

    logger.info("Concluído: %d ok, %d falha(s)", ok, fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
