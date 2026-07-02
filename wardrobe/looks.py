"""
Engine de composição de looks.

Recebe o acervo (lista de dicts vindos do Postgres) e monta um look coerente:
um item por slot do corpo, respeitando formalidade, estação, ocasião e harmonia
de cor. É LÓGICA PURA — não faz IO nem conhece Telegram/Supabase — para ser
reaproveitada pelo app futuro. A camada de bot só fornece os dados e apresenta.

Regra de slots:
  look = (full_body)  OU  (top + bottom)   + footwear
         + opcionalmente outerwear / bag / 1 accessory
Exclui por padrão lingerie/sleepwear/beachwear (beachwear volta se ocasião=praia,
sleepwear se ocasião=casa).
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from . import style_profile
from .schema import (
    Category, ColorFamily, Formality, Material, Occasion, Pattern, Season,
    Subcategory,
)

# Escala ordenada de formalidade -> permite medir "distância" entre peças.
_FORMALITY_ORDER = [
    Formality.CASUAL,
    Formality.SMART_CASUAL,
    Formality.TRABALHO,
    Formality.COCKTAIL,
    Formality.GALA,
]
FORMALITY_RANK = {f.value: i for i, f in enumerate(_FORMALITY_ORDER)}

# Default genérico (sem perfil de coloração): neutros clássicos combinam com tudo;
# o resto é cor "statement" (no máx. uma por look).
_DEFAULT_NEUTRALS = {
    ColorFamily.PRETO.value,
    ColorFamily.BRANCO.value,
    ColorFamily.CINZA.value,
    ColorFamily.BEGE.value,
    ColorFamily.MARROM.value,
    ColorFamily.DOURADO.value,
    ColorFamily.PRATEADO.value,
    ColorFamily.MULTICOR.value,
}

# Neutros efetivos: a paleta ativa manda. Para inverno frio, bege/marrom/dourado
# saem dos neutros (estão na lista 'evita' do perfil) — sem isso, o fallback do
# motor de regras ancorava looks justamente nas cores que apagam a cliente.
NEUTRALS = style_profile.engine_neutrals() or _DEFAULT_NEUTRALS

# Cores que a paleta pede para evitar: o motor DEMOVE (prefere alternativas),
# mas não bloqueia — a peça existe no acervo e pode ser a única do slot.
AVOID = style_profile.engine_avoid()

# Categorias que não entram num look "de rua" comum.
_EXCLUDED_DEFAULT = {
    Category.LINGERIE.value,
    Category.SLEEPWEAR.value,
    Category.BEACHWEAR.value,
}

# Formalidade-alvo sugerida por ocasião (usada quando o usuário pede /look <ocasião>).
_OCCASION_FORMALITY = {
    Occasion.DIA_A_DIA.value: Formality.CASUAL.value,
    Occasion.CASA.value: Formality.CASUAL.value,
    Occasion.ACADEMIA.value: Formality.CASUAL.value,
    Occasion.PRAIA.value: Formality.CASUAL.value,
    Occasion.VIAGEM.value: Formality.CASUAL.value,
    Occasion.ENCONTRO.value: Formality.SMART_CASUAL.value,
    Occasion.ALMOCO_AMIGAS.value: Formality.SMART_CASUAL.value,
    Occasion.JANTAR.value: Formality.SMART_CASUAL.value,
    Occasion.ANIVERSARIO_INFANTIL.value: Formality.SMART_CASUAL.value,
    Occasion.TRABALHO.value: Formality.TRABALHO.value,
    Occasion.FESTA.value: Formality.COCKTAIL.value,
    Occasion.CASAMENTO.value: Formality.GALA.value,
}

# Apelidos em pt-BR (texto livre do comando) -> valor do Enum.
_OCCASION_ALIASES = {
    "dia": Occasion.DIA_A_DIA.value,
    "diaadia": Occasion.DIA_A_DIA.value,
    "dia_a_dia": Occasion.DIA_A_DIA.value,
    "trabalho": Occasion.TRABALHO.value,
    "work": Occasion.TRABALHO.value,
    "festa": Occasion.FESTA.value,
    "balada": Occasion.FESTA.value,
    "casamento": Occasion.CASAMENTO.value,
    "praia": Occasion.PRAIA.value,
    "academia": Occasion.ACADEMIA.value,
    "treino": Occasion.ACADEMIA.value,
    "viagem": Occasion.VIAGEM.value,
    "encontro": Occasion.ENCONTRO.value,
    "date": Occasion.ENCONTRO.value,
    "almoco": Occasion.ALMOCO_AMIGAS.value,
    "almoço": Occasion.ALMOCO_AMIGAS.value,
    "amigas": Occasion.ALMOCO_AMIGAS.value,
    "jantar": Occasion.JANTAR.value,
    "janta": Occasion.JANTAR.value,
    "aniversario": Occasion.ANIVERSARIO_INFANTIL.value,
    "aniversário": Occasion.ANIVERSARIO_INFANTIL.value,
    "festinha": Occasion.ANIVERSARIO_INFANTIL.value,
    "infantil": Occasion.ANIVERSARIO_INFANTIL.value,
    "casa": Occasion.CASA.value,
}
_SEASON_ALIASES = {
    "verao": Season.VERAO.value,
    "verão": Season.VERAO.value,
    "inverno": Season.INVERNO.value,
    "outono": Season.OUTONO.value,
    "primavera": Season.PRIMAVERA.value,
}

# --------------------------------------------------------------------------- #
# Temperatura — sinal mais honesto que a estação para decidir AGASALHO.
# (No Brasil um outono pode ser frio ou quente; aqui o que manda é o clima real.)
# Frio  -> casaco recomendado + tecidos quentes
# Ameno -> casaco opcional
# Quente-> sem casaco + tecidos leves
# --------------------------------------------------------------------------- #
TEMP_FRIO = "frio"
TEMP_AMENO = "ameno"
TEMP_QUENTE = "quente"

_TEMP_ALIASES = {
    "frio": TEMP_FRIO,
    "friozinho": TEMP_FRIO,
    "gelado": TEMP_FRIO,
    "cold": TEMP_FRIO,
    "ameno": TEMP_AMENO,
    "fresco": TEMP_AMENO,
    "ameia": TEMP_AMENO,
    "mild": TEMP_AMENO,
    "quente": TEMP_QUENTE,
    "calor": TEMP_QUENTE,
    "quentinho": TEMP_QUENTE,
    "hot": TEMP_QUENTE,
}

# Materiais que aquecem (favorecidos no frio) e os leves/frescos (favorecidos no quente).
# Demoção, não bloqueio: numa peça única do slot ela entra mesmo "errada".
WARM_MATERIALS = {
    Material.LA.value, Material.TRICO.value, Material.CASHMERE.value, Material.MOHAIR.value,
    Material.TWEED.value, Material.VELUDO.value, Material.COURO.value,
    Material.COURO_SINTETICO.value, Material.MOLETOM.value, Material.MALHA.value,
    Material.CROCHE.value,
}
LIGHT_MATERIALS = {
    Material.LINHO.value, Material.ALGODAO.value, Material.SEDA.value, Material.VISCOSE.value,
    Material.CETIM.value, Material.RENDA.value, Material.LYCRA.value, Material.NYLON.value,
}


def parse_temperature(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _TEMP_ALIASES:
            return _TEMP_ALIASES[token]
    return None


# Eixo de OUSADIA dos looks curados (discreto < equilibrado < ousado).
BOLD_DISCRETO = "discreto"
BOLD_EQUILIBRADO = "equilibrado"
BOLD_OUSADO = "ousado"
_BOLD_ALIASES = {
    "discreto": BOLD_DISCRETO,
    "classico": BOLD_DISCRETO,
    "clássico": BOLD_DISCRETO,
    "basico": BOLD_DISCRETO,
    "sobrio": BOLD_DISCRETO,
    "equilibrado": BOLD_EQUILIBRADO,
    "medio": BOLD_EQUILIBRADO,
    "ousado": BOLD_OUSADO,
    "arrojado": BOLD_OUSADO,
    "statement": BOLD_OUSADO,
}


def parse_boldness(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _BOLD_ALIASES:
            return _BOLD_ALIASES[token]
    return None


def temp_from_celsius(celsius: float) -> str:
    """Mapeia °C -> faixa. Fonte única do limiar (usada pelo botão 'clima daqui')."""
    if celsius < 15:
        return TEMP_FRIO
    if celsius < 24:
        return TEMP_AMENO
    return TEMP_QUENTE


def _temp_material_penalty(g: dict, temperature: Optional[str]) -> int:
    """0 = material adequado/neutro p/ a temperatura; 1 = na contramão (demovido)."""
    if not temperature:
        return 0
    mat = g.get("material")
    if not mat:
        return 0  # material desconhecido: não penaliza
    if temperature == TEMP_FRIO:
        return 1 if mat in LIGHT_MATERIALS else 0
    if temperature == TEMP_QUENTE:
        return 1 if mat in WARM_MATERIALS else 0
    return 0  # ameno: tudo serve


def wants_outerwear(temperature: Optional[str], season: Optional[str], rng: random.Random) -> bool:
    """Política de casaco: frio pede, quente proíbe, ameno é opcional. Sem
    temperatura, cai no comportamento antigo (estação fria sugere casaco)."""
    if temperature == TEMP_QUENTE:
        return False
    if temperature == TEMP_FRIO:
        return True
    if temperature == TEMP_AMENO:
        # ameno também pede uma 3ª peça (casaco leve) — quase sempre, pelo estilo
        # da cliente (camada = parte do arrojo), não só no frio.
        return rng.random() < 0.85
    # sem temperatura: favorece a camada (o look ganha personalidade com ela)
    return season in (Season.OUTONO.value, Season.INVERNO.value) or rng.random() < 0.55


def cold_without_coat(pieces: list[dict], temperature: Optional[str]) -> bool:
    """Está frio mas o look saiu sem casaco (acervo não tem outerwear elegível)."""
    if temperature != TEMP_FRIO:
        return False
    return not any(p.get("category") == Category.OUTERWEAR.value for p in pieces)


@dataclass
class Look:
    """Resultado da composição: peças escolhidas + slots essenciais que faltaram."""

    pieces: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # categorias essenciais ausentes
    occasion: Optional[str] = None
    season: Optional[str] = None
    temperature: Optional[str] = None

    @property
    def complete(self) -> bool:
        return not self.missing


def parse_occasion(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _OCCASION_ALIASES:
            return _OCCASION_ALIASES[token]
    return None


def parse_season(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _SEASON_ALIASES:
            return _SEASON_ALIASES[token]
    return None


# --------------------------------------------------------------------------- #
# Filtros de coerência
# --------------------------------------------------------------------------- #
def _formality_ok(target_rank: Optional[int], g: dict, tol: int = 1) -> bool:
    if target_rank is None:
        return True
    r = FORMALITY_RANK.get(g.get("formality"))
    return r is not None and abs(r - target_rank) <= tol


def _season_ok(g: dict, season: Optional[str]) -> bool:
    if not season:
        return True
    seasons = g.get("seasons") or []
    return not seasons or season in seasons  # vazio = peça atemporal


_BOLD_COLOR_PARTNERS = {
    "vermelho": {"rosa", "laranja", "verde", "azul"},
    "rosa": {"vermelho", "roxo", "laranja", "verde"},
    "laranja": {"vermelho", "rosa", "amarelo", "azul"},
    "amarelo": {"laranja", "verde", "roxo", "azul"},
    "verde": {"amarelo", "azul", "vermelho", "rosa", "roxo"},
    "azul": {"verde", "roxo", "laranja", "amarelo", "vermelho"},
    "roxo": {"azul", "rosa", "amarelo", "verde"},
}

_STATEMENT_MATERIALS = {
    Material.COURO.value,
    Material.COURO_SINTETICO.value,
    Material.RENDA.value,
    Material.CETIM.value,
    Material.VELUDO.value,
    Material.TWEED.value,
    Material.CROCHE.value,
}

_LIGHT_LAYER_SUBCATEGORIES = {
    Subcategory.COLETE.value,
    Subcategory.KIMONO.value,
}


def _color_ok(colors: list[str], candidate: str, boldness: Optional[str] = None) -> bool:
    """Valida a paleta sem transformar coerência em uniformidade.

    Discreto/equilibrado preservam a regra segura de uma cor marcante. Ousado
    aceita até três cores marcantes quando cada nova cor cria uma relação
    intencional (análoga ou de contraste) com a paleta já escolhida.
    """
    if not candidate or candidate in NEUTRALS:
        return True
    statements = [c for c in colors if c and c not in NEUTRALS]
    distinct = set(statements)
    if not distinct or candidate in distinct:
        return True
    if boldness != BOLD_OUSADO or len(distinct) >= 3:
        return False
    return any(candidate in _BOLD_COLOR_PARTNERS.get(color, set()) for color in distinct)


def _boldness_score(g: dict, chosen: list[dict], boldness: Optional[str]) -> int:
    """Quanto a peça acrescenta interesse visual ao look já escolhido."""
    if boldness != BOLD_OUSADO:
        return 0
    score = 0
    primary_color = g.get("primary_color")
    if primary_color and primary_color not in NEUTRALS:
        chosen_colors = {
            x.get("primary_color") for x in chosen
            if x.get("primary_color") and x.get("primary_color") not in NEUTRALS
        }
        # Ousadia vem de contraste intencional, não de repetir a cor já usada.
        score += 4 if primary_color not in chosen_colors else 1

    pattern = g.get("pattern")
    if pattern not in (None, Pattern.LISO.value):
        score += 3
        chosen_patterns = {
            x.get("pattern") for x in chosen
            if x.get("pattern") not in (None, Pattern.LISO.value)
        }
        if pattern not in chosen_patterns:
            score += 2
        if pattern == Pattern.ANIMAL_PRINT.value:
            score += 2
    if g.get("material") in _STATEMENT_MATERIALS:
        score += 1
    # High-low: uma diferença moderada de formalidade deixa o look menos óbvio.
    ranks = [FORMALITY_RANK.get(x.get("formality")) for x in chosen]
    rank = FORMALITY_RANK.get(g.get("formality"))
    if rank is not None and any(r is not None and abs(rank - r) == 1 for r in ranks):
        score += 1
    return score


def _hot_layer_ok(g: dict) -> bool:
    """No calor, aceita só uma terceira peça plausivelmente leve."""
    material = g.get("material")
    if material in WARM_MATERIALS:
        return False
    return (
        g.get("subcategory") in _LIGHT_LAYER_SUBCATEGORIES
        or material in LIGHT_MATERIALS
    )


def _cands(
    pools: list[list[dict]], category: str, target_rank, season, colors, temperature=None,
    boldness=None, chosen=None,
) -> list[dict]:
    """Candidatos do slot, tentando cada pool em ordem (preferida -> ampla).

    Dentro de cada pool, peças em cores 'evita' da paleta ou em material errado
    para a temperatura são DEMOVIDAS (só entram se não houver alternativa) — pega
    sempre o melhor estrato disponível, mas nunca bloqueia (acervo é pequeno).
    """
    for pool in pools:
        hits = [
            g
            for g in pool
            if g.get("category") == category
            and _formality_ok(target_rank, g)
            and _season_ok(g, season)
            and _color_ok(colors, g.get("primary_color"), boldness)
        ]
        if hits:
            def _penalty(g: dict) -> int:
                color_pen = 1 if g.get("primary_color") in AVOID else 0
                return color_pen + _temp_material_penalty(g, temperature)

            best = min(_penalty(g) for g in hits)
            best_hits = [g for g in hits if _penalty(g) == best]
            if boldness == BOLD_OUSADO:
                top_score = max(_boldness_score(g, chosen or [], boldness) for g in best_hits)
                return [
                    g for g in best_hits
                    if _boldness_score(g, chosen or [], boldness) == top_score
                ]
            return best_hits
    return []


def missing_slots(pieces: list[dict]) -> list[str]:
    """Slots essenciais ausentes num conjunto de peças (top+bottom ou full_body, + footwear)."""
    present = {g.get("category") for g in pieces}
    missing: list[str] = []
    if Category.FULL_BODY.value not in present:
        if Category.TOP.value not in present:
            missing.append(Category.TOP.value)
        if Category.BOTTOM.value not in present:
            missing.append(Category.BOTTOM.value)
    if Category.FOOTWEAR.value not in present:
        missing.append(Category.FOOTWEAR.value)
    return missing


def candidates(
    garments: list[dict],
    occasion: Optional[str] = None,
    limit: int = 60,
    temperature: Optional[str] = None,
) -> list[dict]:
    """Acervo elegível para o estilista IA: remove categorias incompatíveis com um
    look de rua e prioriza as peças da ocasião. Coerência de cor/taste fica com o
    estilista — aqui só garantimos que as peças existem e fazem sentido no slot."""
    excluded = set(_EXCLUDED_DEFAULT)
    if occasion == Occasion.PRAIA.value:
        excluded.discard(Category.BEACHWEAR.value)
    if occasion == Occasion.CASA.value:
        excluded.discard(Category.SLEEPWEAR.value)
    pool = [g for g in garments if g.get("category") not in excluded]
    # Ordena por: 1) peça da ocasião primeiro; 2) cor favorável antes de cor
    # 'evita' — assim o corte de MAX_IMAGES do estilista gasta o orçamento de
    # fotos nas peças que mais favorecem a cliente.
    pool.sort(
        key=lambda g: (
            (0 if occasion in (g.get("occasions") or []) else 1) if occasion else 0,
            _temp_material_penalty(g, temperature),
            1 if g.get("primary_color") in AVOID else 0,
        )
    )
    return pool[:limit]


# --------------------------------------------------------------------------- #
# Composição (motor de regras — usado como fallback do estilista IA)
# --------------------------------------------------------------------------- #
def compose(
    garments: list[dict],
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    temperature: Optional[str] = None,
    boldness: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Look:
    rng = rng or random

    excluded = set(_EXCLUDED_DEFAULT)
    if occasion == Occasion.PRAIA.value:
        excluded.discard(Category.BEACHWEAR.value)
    if occasion == Occasion.CASA.value:
        excluded.discard(Category.SLEEPWEAR.value)

    pool_all = [g for g in garments if g.get("category") not in excluded]
    if occasion:
        pool_pref = [g for g in pool_all if occasion in (g.get("occasions") or [])]
        pools = [pool_pref, pool_all]
    else:
        pools = [pool_all]

    target_rank: Optional[int] = None
    if occasion and occasion in _OCCASION_FORMALITY:
        target_rank = FORMALITY_RANK[_OCCASION_FORMALITY[occasion]]

    chosen: list[dict] = []
    colors: list[str] = []

    def commit(g: dict) -> None:
        chosen.append(g)
        colors.append(g.get("primary_color"))

    # --- base: full_body OU top+bottom ---
    def slot(category: str) -> list[dict]:
        return _cands(
            pools, category, target_rank, season, colors, temperature,
            boldness, chosen,
        )

    full_cands = slot(Category.FULL_BODY.value)
    top_cands = slot(Category.TOP.value)
    bottom_cands = slot(Category.BOTTOM.value)

    prefer_full = bool(full_cands) and (not (top_cands and bottom_cands) or rng.random() < 0.4)
    if prefer_full:
        commit(rng.choice(full_cands))
    else:
        if top_cands:
            commit(rng.choice(top_cands))
        # o bottom precisa harmonizar com a cor já escolhida
        bottom_cands = slot(Category.BOTTOM.value)
        if bottom_cands:
            commit(rng.choice(bottom_cands))

    # se não havia ocasião, fixa a formalidade-alvo pela peça-base escolhida
    if target_rank is None and chosen:
        target_rank = FORMALITY_RANK.get(chosen[0].get("formality"))

    # --- calçado (essencial) ---
    shoe_cands = slot(Category.FOOTWEAR.value)
    if shoe_cands:
        commit(rng.choice(shoe_cands))

    # --- extras opcionais ---
    # Camada: frio pede; no calor, ousado aceita somente colete/kimono ou material
    # leve. Materiais quentes já são favorecidos pelo _cands no frio.
    add_outerwear = boldness == BOLD_OUSADO or wants_outerwear(temperature, season, rng)
    if add_outerwear:
        outer = slot(Category.OUTERWEAR.value)
        if temperature == TEMP_QUENTE:
            outer = [g for g in outer if _hot_layer_ok(g)]
        if outer:
            commit(rng.choice(outer))

    if boldness == BOLD_OUSADO or rng.random() < 0.6:
        bag = slot(Category.BAG.value)
        if bag:
            commit(rng.choice(bag))

    if boldness == BOLD_OUSADO or rng.random() < 0.5:
        acc = slot(Category.ACCESSORY.value)
        if acc:
            commit(rng.choice(acc))

    return Look(
        pieces=chosen,
        missing=missing_slots(chosen),
        occasion=occasion,
        season=season,
        temperature=temperature,
    )
