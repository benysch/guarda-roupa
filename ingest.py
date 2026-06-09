#!/usr/bin/env python3
"""
Ingestão batch: varre uma pasta de fotos -> pipeline -> relatório JSON.

Pipeline (ordem que evita lixo no Storage):
    normalizar (Pillow) + sha256 -> dedupe -> extrair (Gemini) -> upload -> insert

Cada item é isolado em try/except: uma falha nunca derruba o lote. Reexecutar
na mesma pasta é seguro (dedupe por content_hash).

Uso:
    python ingest.py ./fotos [--workers 4] [--report relatorio.json]
"""

import argparse
import dataclasses
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from wardrobe import embeddings, storage
from wardrobe.config import get_settings
from wardrobe.extractor import ExtractionError, extract_garment
from wardrobe.imaging import (
    SUPPORTED_SUFFIXES,
    ImageValidationError,
    normalize_image,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")


@dataclasses.dataclass
class ItemResult:
    file: str
    outcome: str  # processed | skipped_duplicate | skipped_not_garment | needs_review | failed
    garment_id: str | None = None
    detail: str | None = None


def _iter_images(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def process_one(path: Path) -> ItemResult:
    name = str(path)
    try:
        raw = path.read_bytes()
        norm = normalize_image(raw)
    except (ImageValidationError, OSError) as exc:
        return ItemResult(name, "failed", detail=f"imagem inválida: {exc}")

    # dedupe — barato e evita chamar o Gemini à toa
    existing = storage.find_existing_id(norm.content_hash)
    if existing:
        return ItemResult(name, "skipped_duplicate", garment_id=existing)

    # extração
    try:
        meta = extract_garment(norm.jpeg_bytes)
    except ExtractionError as exc:
        return ItemResult(name, "failed", detail=str(exc))

    if not meta.is_garment:
        return ItemResult(name, "skipped_not_garment")

    threshold = get_settings().confidence_threshold
    status = "needs_review" if meta.extraction_confidence < threshold else "processed"

    # upload -> insert (peça válida; só agora ocupamos o Storage)
    garment_id = storage.new_garment_id()
    try:
        image_path = storage.upload_image(garment_id, norm.jpeg_bytes)
        storage.insert_garment(
            image_path=image_path,
            content_hash=norm.content_hash,
            meta=meta,
            garment_id=garment_id,
            status=status,
        )
    except Exception as exc:  # rede/DB/quota — registra e segue
        return ItemResult(name, "failed", garment_id=garment_id, detail=f"persistência: {exc}")

    # embedding p/ busca semântica — não-fatal: a peça já está persistida
    try:
        g = storage.get_garment(garment_id)
        storage.update_embedding(garment_id, embeddings.embed(embeddings.garment_text(g)))
    except Exception as exc:
        logger.warning("embedding falhou para %s: %s", garment_id, exc)

    outcome = "needs_review" if status == "needs_review" else "processed"
    return ItemResult(name, outcome, garment_id=garment_id,
                      detail=f"{meta.category.value}/{meta.subcategory.value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestão batch do guarda-roupa")
    parser.add_argument("folder", type=Path, help="Pasta com as fotos")
    parser.add_argument("--workers", type=int, default=4,
                        help="Threads paralelas (respeite o rate limit do Gemini)")
    parser.add_argument("--report", type=Path, default=Path("relatorio_ingestao.json"))
    args = parser.parse_args()

    if not args.folder.is_dir():
        logger.error("Pasta não encontrada: %s", args.folder)
        return 2

    # valida config cedo (falha clara se faltar env)
    get_settings()

    images = list(_iter_images(args.folder))
    if not images:
        logger.warning("Nenhuma imagem suportada em %s", args.folder)
        return 0

    logger.info("Encontradas %d imagens. Processando com %d workers...",
                len(images), args.workers)

    results: list[ItemResult] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, p): p for p in images}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            logger.info("[%s] %s %s", res.outcome, res.file, res.detail or "")

    summary: dict[str, int] = {}
    for r in results:
        summary[r.outcome] = summary.get(r.outcome, 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "folder": str(args.folder),
        "total": len(results),
        "summary": summary,
        "items": [dataclasses.asdict(r) for r in results],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    logger.info("Relatório: %s | resumo: %s", args.report, summary)

    return 1 if summary.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
