"""
Lógica dos endpoints JSON consumidos pelo site (look e busca semântica).

Não conhece HTTP — recebe parâmetros já parseados e devolve dicts prontos para
serializar. O entrypoint serverless (`api/telegram.py`) faz o roteamento por path
e a checagem do segredo, e chama estas funções. Reaproveita stylist/looks/
embeddings/storage (mesma fonte de verdade do bot).
"""

import json

from . import capsule, embeddings, looks, storage, stylist


def _piece(g: dict) -> dict:
    return {
        "id": g["id"],
        "category": g.get("category"),
        "subcategory": g.get("subcategory"),
        "primary_color": g.get("primary_color"),
        "brand": g.get("brand"),
        "description": g.get("description"),
    }


def compose_look(occasion_raw: str = "", season_raw: str = "") -> dict:
    """Híbrido estilista IA + regras. Devolve peças escolhidas + justificativa."""
    occasion = looks.parse_occasion(occasion_raw or "")
    season = looks.parse_season(season_raw or "")
    garments = storage.fetch_garments()

    cands = looks.candidates(garments, occasion)
    pieces, rationale = [], None
    if cands:
        by_id = {g["id"]: g for g in cands}
        try:
            sl = stylist.style_look(cands, occasion=occasion, season=season)
            chosen = [by_id[i] for i in sl.garment_ids if i in by_id]
            if chosen:
                pieces, rationale = chosen, sl.rationale
        except Exception:  # estilista falhou -> motor de regras
            pieces = []
    if not pieces:
        pieces = looks.compose(garments, occasion=occasion, season=season).pieces

    return {
        "occasion": occasion,
        "season": season,
        "rationale": rationale,
        "missing": looks.missing_slots(pieces),
        "pieces": [_piece(g) for g in pieces],
    }


def search(query: str, k: int = 8) -> dict:
    """Busca semântica: embeda a consulta e devolve as peças mais próximas."""
    results = []
    if query:
        vec = embeddings.embed(query, embeddings.TASK_QUERY)
        results = storage.match_garments(vec, match_count=k)
    return {
        "query": query,
        "results": [{**_piece(m), "similarity": m.get("similarity")} for m in results],
    }


def pack_capsule(trip_raw: str = "", include_bag: bool = True) -> dict:
    """Monta a mala mínima da viagem (engine capsule) a partir do plano dia-a-dia.

    `trip_raw` é o JSON dos dias: ``[{"season": "inverno", "occasions":
    ["trabalho", "festa"]}, ...]``. Cada ocasião de um dia vira um look (TripSlot)
    com o clima daquele dia. Devolve a mala agrupada por categoria, os looks de
    cada dia e os slots não cobertos (lacunas).
    """
    days_in = json.loads(trip_raw) if trip_raw else []

    slots: list[capsule.TripSlot] = []
    spans: list[tuple[int, int, str | None]] = []  # (início, fim, estação) por dia
    for di, day in enumerate(days_in):
        season = looks.parse_season(day.get("season") or "")
        start = len(slots)
        for occ_raw in day.get("occasions") or []:
            occ = looks.parse_occasion(occ_raw or "")
            label = f"Dia {di + 1}"
            if occ:
                label += f" — {occ.replace('_', ' ')}"
            slots.append(capsule.TripSlot(label=label, occasion=occ, season=season))
        spans.append((start, len(slots), season))

    garments = storage.fetch_garments()
    cap = capsule.pack(garments, slots, include_bag=include_bag)

    days_out = [
        {
            "label": f"Dia {di + 1}",
            "season": season,
            "looks": [
                {
                    "label": sl.slot.label,
                    "occasion": sl.slot.occasion,
                    "missing": sl.missing,
                    "pieces": [_piece(p) for p in sl.pieces],
                }
                for sl in cap.looks[start:end]
            ],
        }
        for di, (start, end, season) in enumerate(spans)
    ]

    return {
        "include_bag": include_bag,
        "count": len(cap.pieces),
        "suitcase": {
            cat: [_piece(p) for p in items] for cat, items in cap.by_category().items()
        },
        "days": days_out,
        "uncovered": [
            {"label": sl.slot.label, "missing": sl.missing} for sl in cap.uncovered
        ],
    }


def similar(garment_id: str, k: int = 6) -> dict:
    """Peças parecidas com uma peça (vizinhos por embedding)."""
    results = storage.similar_garments(garment_id, k) if garment_id else []
    return {
        "id": garment_id,
        "results": [{**_piece(m), "similarity": m.get("similarity")} for m in results],
    }
