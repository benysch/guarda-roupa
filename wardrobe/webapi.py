"""
Lógica dos endpoints JSON consumidos pelo site (look e busca semântica).

Não conhece HTTP — recebe parâmetros já parseados e devolve dicts prontos para
serializar. O entrypoint serverless (`api/telegram.py`) faz o roteamento por path
e a checagem do segredo, e chama estas funções. Reaproveita stylist/looks/
embeddings/storage (mesma fonte de verdade do bot).
"""

import random

from . import capsule, embeddings, looks, storage


def _combo_key(*parts) -> str:
    return "/".join(p or "—" for p in parts)


def _piece(g: dict) -> dict:
    return {
        "id": g["id"],
        "category": g.get("category"),
        "subcategory": g.get("subcategory"),
        "primary_color": g.get("primary_color"),
        "shade": g.get("shade"),
        "brand": g.get("brand"),
        "description": g.get("description"),
    }


def _look_out(occasion, season, temperature, boldness, pieces, rationale, look_id=None, model_image=None) -> dict:
    return {
        "look_id": look_id,  # id da curadoria (None se veio do motor de regras) -> feedback
        "model_image": model_image,  # chave do objeto da foto na modelo (None = sem foto cacheada)
        "occasion": occasion,
        "season": season,
        "temperature": temperature,
        "boldness": boldness,
        "rationale": rationale,
        "missing": looks.missing_slots(pieces),
        "cold_without_coat": looks.cold_without_coat(pieces, temperature),
        "pieces": [_piece(g) for g in pieces],
    }


def compose_look(
    occasion_raw: str = "", season_raw: str = "", temp_raw: str = "", bold_raw: str = ""
) -> dict:
    """Look pré-computado (curadoria do Claude) quando existe; senão, motor de regras.

    SEM IA em tempo real: a curadoria é gerada offline e cacheada em `curated_looks`.
    `temp_raw` = faixa de temperatura (frio/ameno/quente); `bold_raw` = ousadia
    (discreto/equilibrado/ousado). Sem curadoria no nível solicitado, usa o motor
    de regras preservando a ousadia.
    """
    occasion = looks.parse_occasion(occasion_raw or "")
    season = looks.parse_season(season_raw or "")
    temperature = looks.parse_temperature(temp_raw or "")
    boldness = looks.parse_boldness(bold_raw or "")
    garments = storage.fetch_garments()
    by_id = {g["id"]: g for g in garments}

    # 1) curadoria pronta. Primeiro relaxa o CLIMA mantendo o nível de ousadia;
    #    se ainda não houver curadoria, o motor de regras preserva o nível pedido.
    curated = storage.get_curated_looks(occasion, season, temperature, boldness)
    if not curated and boldness and temperature:
        curated = storage.get_curated_looks(occasion, season, None, boldness)
    # Se o nível pedido não tem curadoria, o motor de regras respeita melhor a
    # intenção do que escolher silenciosamente um look de outro nível.
    if curated:
        row = random.choice(curated)
        pieces = [by_id[i] for i in (row.get("garment_ids") or []) if i in by_id]
        if pieces:
            return _look_out(
                occasion, season, temperature, row.get("boldness"), pieces,
                row.get("rationale"), look_id=row.get("id"),
                model_image=row.get("model_image"),
            )

    # 2) fallback: motor de regras (instantâneo, sem IA) + registra o combo pedido
    storage.log_request("look", _combo_key(occasion, season, temperature, boldness))
    pieces = looks.compose(
        garments, occasion=occasion, season=season, temperature=temperature,
        boldness=boldness,
    ).pieces
    return _look_out(occasion, season, temperature, boldness, pieces, None)


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

    # cápsula pré-computada quando existe; senão cai nas regras (capsule.pack)
    curated = storage.get_curated_capsule(days, occasion, night, season, None)
    if curated:
        return random.choice(curated)["payload"]
    storage.log_request("capsule", _combo_key(str(days), occasion, night, season))

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
