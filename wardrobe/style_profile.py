"""
Perfil de estilo da cliente + base de conhecimento de coloração pessoal.

Single-user por ora (a Beny). A coloração ativa é um palpite ajustável — se ela
fizer a análise formal, basta trocar `ACTIVE_PALETTE`. O estilista (stylist.py)
lê `prompt_fragment()` para favorecer as cores que iluminam e evitar as que apagam.
"""

# Coloração pessoal ativa da cliente.
ACTIVE_PALETTE = "inverno_frio"

# Bases de conhecimento de coloração (análise sazonal). Adicione outras conforme
# necessário; cada uma vira um fragmento de prompt para o estilista.
PALETTES: dict[str, dict] = {
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
    },
}


def prompt_fragment(palette: str = ACTIVE_PALETTE) -> str:
    """Trecho de prompt descrevendo a coloração da cliente para o estilista IA."""
    p = PALETTES[palette]
    return (
        f"Coloração pessoal da cliente: {p['nome']} — subtom {p['subtom']}.\n"
        f"Cores que a FAVORECEM: {', '.join(p['favorece'])}.\n"
        f"Cores a EVITAR (apagam/amarelam a pele): {', '.join(p['evita'])}.\n"
        f"Metais: {p['metais']}. {p['extra']}."
    )
