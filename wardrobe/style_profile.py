"""
Perfil de estilo da cliente + base de conhecimento de coloração pessoal.

Single-user por ora (a Muri — usuária final; o Beny constrói e alimenta os dados). A coloração ativa é um palpite ajustável — se ela
fizer a análise formal, basta trocar `ACTIVE_PALETTE`. O estilista (stylist.py)
lê `prompt_fragment()` para favorecer as cores que iluminam e evitar as que apagam.
"""

# Coloração pessoal ativa da cliente.
# FLEXÍVEL por decisão do Muriel (2026-06-14): as referências reais da esposa
# (exemplos de looks/) mostram gosto QUENTE/terroso + textura + camadas, contrariando
# o palpite de "inverno frio". Em vez de trocar por outra regra rígida, soltamos a
# premissa: nenhuma cor é demovida; prioriza-se harmonia, textura e ousadia ancorada.
# O conhecimento de inverno_frio fica guardado (trocar ACTIVE_PALETTE se ela fizer
# a análise formal de coloração).
ACTIVE_PALETTE = "flexivel"

# Bases de conhecimento de coloração (análise sazonal). Adicione outras conforme
# necessário; cada uma vira um fragmento de prompt para o estilista.
PALETTES: dict[str, dict] = {
    "flexivel": {
        "nome": "Flexível — sem coloração fixa",
        "subtom": "neutro (sem regra rígida de subtom)",
        "favorece": [
            "praticamente todas as cores",
            "tons quentes/terrosos (oliva, terracota, mostarda, camel, ferrugem)",
            "tons frios e joia (marinho, vinho, esmeralda, fúcsia)",
            "neutros (preto, branco, cinza, bege, marrom)",
        ],
        "evita": ["nenhuma cor é proibida — priorize harmonia, textura e camadas"],
        "metais": "prata ou dourado, conforme o look",
        "extra": "valorize TEXTURA e SOBREPOSIÇÃO; ouse em pares de cor desde que "
        "uma peça seja a estrela e o resto ancore",
        "combinacao": [
            "uma peça statement (cor/textura/estampa) + resto em neutros que aterram",
            "misturar texturas (tweed, tricô, linho, jeans, couro) eleva o look",
            "camadas (sobrecamisa, colete, blazer, kimono) dão personalidade",
            "pares quentes são bem-vindos: terracota + jeans, oliva + preto, marinho + mostarda",
            "estampa + estampa funciona se uma for neutra (oncinha, listra)",
        ],
        # engine: sem demoção de cor — todas concorrem igual; neutros amplos
        # (neutros_engine omitido -> default amplo de looks.py; evitar_engine vazio).
        "evitar_engine": [],
    },
    "inverno_frio": {
        "nome": "Inverno Frio (cool winter)",
        "subtom": "frio (pele de subtom rosado/azulado)",
        "favorece": [
            "branco puro/ótico",
            "preto",
            "azul-marinho",
            "cinza",
            "tons joia (esmeralda, safira, azul-royal)",
            "vinho/bordô",
            "framboesa",
            "fúcsia/magenta",
            "vermelho frio (cereja)",
            "rosa frio/pink",
            "roxo/ametista",
            "verde-pinheiro",
            "azul gelado",
        ],
        "evita": [
            "bege",
            "creme",
            "marrom quente/camel",
            "laranja",
            "coral",
            "pêssego",
            "amarelo-ouro",
            "mostarda",
            "verde-oliva",
            "tons terrosos",
            "tons empoeirados/muted",
        ],
        "metais": "prata / branco (evitar dourado)",
        "extra": "alto contraste valoriza (ex.: preto + branco); cores claras e saturadas",
        # Teoria de COMBINAÇÃO do inverno frio (não só quais cores, mas como
        # juntá-las): a regra mestra é repetir no look o alto contraste natural
        # da aparência. Fonte: análise sazonal de 12 estações (true/cool winter).
        "combinacao": [
            "regra mestra: todo look deve ter ALTO CONTRASTE de claro/escuro — "
            "uma peça bem escura com uma bem clara ou vívida; looks inteiros em "
            "tons médios apagam, mesmo usando só cores da paleta",
            "preto + branco puro é a dupla assinatura desta coloração",
            "pastéis gelados (rosa gelo, azul gelado) são ACENTO junto a um "
            "neutro escuro (preto, marinho, chumbo) — nunca o look inteiro",
            "tom joia como statement, ancorado por neutro escuro: ruby + preto, "
            "esmeralda + chumbo, fúcsia + marinho, cobalto + marinho",
            "neutro claro + acento vibrante também funciona: cinza claro + pink",
            "monocromático só se for escuro e nítido (all-black, marinho total); "
            "evitar tonal de tons médios/suaves",
            "nunca misturar com terrosos/quentes; tons empoeirados (mesmo frios, "
            "ex. lavanda dusty) apagam por falta de intensidade",
        ],
        # Visão do MOTOR DE REGRAS (looks.py) sobre a paleta, em valores de
        # ColorFamily. Neutros são paleta-dependentes: para inverno frio,
        # bege/marrom/dourado NÃO são neutros (estão na lista 'evita').
        "neutros_engine": ["preto", "branco", "cinza", "prateado", "multicor"],
        "evitar_engine": ["bege", "marrom", "dourado", "laranja", "amarelo"],
    },
}


def engine_neutrals(palette: str = ACTIVE_PALETTE) -> set[str] | None:
    """Famílias de cor que o motor de regras trata como neutras para esta paleta.

    Devolve None se a paleta não definir — o motor usa então o default genérico.
    """
    vals = PALETTES.get(palette, {}).get("neutros_engine")
    return set(vals) if vals else None


def engine_avoid(palette: str = ACTIVE_PALETTE) -> set[str]:
    """Famílias de cor que apagam a cliente: o motor demove (não bloqueia)."""
    return set(PALETTES.get(palette, {}).get("evitar_engine") or [])


def prompt_fragment(palette: str = ACTIVE_PALETTE) -> str:
    """Trecho de prompt descrevendo a coloração da cliente para o estilista IA."""
    p = PALETTES[palette]
    base = (
        f"Coloração pessoal da cliente: {p['nome']} — subtom {p['subtom']}.\n"
        f"Cores que a FAVORECEM: {', '.join(p['favorece'])}.\n"
        f"Cores a EVITAR (apagam/amarelam a pele): {', '.join(p['evita'])}.\n"
        f"Metais: {p['metais']}. {p['extra']}."
    )
    combos = p.get("combinacao")
    if combos:
        base += "\nComo COMBINAR as cores no look:\n" + "\n".join(
            f"- {c}" for c in combos
        )
    return base
