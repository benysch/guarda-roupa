"""
Lógica dos endpoints JSON consumidos pelo site (look e busca semântica).

Não conhece HTTP — recebe parâmetros já parseados e devolve dicts prontos para
serializar. O entrypoint serverless (`api/telegram.py`) faz o roteamento por path
e a checagem do segredo, e chama estas funções. Reaproveita stylist/looks/
embeddings/storage (mesma fonte de verdade do bot).
"""

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


def pack_capsule(
    days_raw: str = "",
    occasion_raw: str = "",
    night_raw: str = "",
    season_raw: str = "",
) -> dict:
    """Mala de viagem: traduz a viagem em TripSlots e empacota com capsule.pack.

    Cada dia gera um slot diurno; se houver ocasião de noite, um slot noturno
    por dia também. Devolve a mala (agrupada por categoria, em ordem de
    empacotamento) e o look de cada slot, com o que faltou.
    """
    try:
        days = max(1, min(14, int(days_raw or "3")))
    except ValueError:
        days = 3
    occasion = looks.parse_occasion(occasion_raw or "")
    night = looks.parse_occasion(night_raw or "")
    season = looks.parse_season(season_raw or "")

    slots: list[capsule.TripSlot] = []
    for d in range(1, days + 1):
        slots.append(capsule.TripSlot(label=f"Dia {d}", occasion=occasion, season=season))
        if night:
            slots.append(
                capsule.TripSlot(label=f"Dia {d} — noite", occasion=night, season=season)
            )

    cap = capsule.pack(storage.fetch_garments(), slots)
    return {
        "days": days,
        "occasion": occasion,
        "night": night,
        "season": season,
        "total": len(cap.pieces),
        "groups": [
            {"category": cat, "pieces": [_piece(g) for g in grp]}
            for cat, grp in cap.by_category().items()
        ],
        "looks": [
            {
                "label": sl.slot.label,
                "occasion": sl.slot.occasion,
                "pieces": [_piece(g) for g in sl.pieces],
                "missing": sl.missing,
            }
            for sl in cap.looks
        ],
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


def similar(garment_id: str, k: int = 6) -> dict:
    """Peças parecidas com uma peça (vizinhos por embedding)."""
    results = storage.similar_garments(garment_id, k) if garment_id else []
    return {
        "id": garment_id,
        "results": [{**_piece(m), "similarity": m.get("similarity")} for m in results],
    }
