"""
Schema de extração de metadados de peças de roupa.

Fonte da verdade do vocabulário: os Enums aqui garantem filtragem determinística
para a composição de looks. O modelo `GarmentMetadata` é passado direto como
`response_schema` ao Gemini (Structured Outputs).

Princípios de design:
- `category` (o "slot" do corpo) primeiro — é a chave da composição: nunca se
  combinam duas peças do mesmo slot, e `full_body` ocupa top+bottom de uma vez.
- Vocabulário fechado vira Enum; texto livre só em `description`/`style_keywords`.
- Modelo PLANO: campos que não se aplicam a uma categoria são Optional e voltam null.
- Guard-rails: `is_garment` (descarta fotos que não são roupa) e
  `extraction_confidence` (manda baixa confiança para revisão).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums — vocabulário fechado (pt-BR para casar com o domínio)
# --------------------------------------------------------------------------- #
class Category(str, Enum):
    """
    O grupo/slot da peça — chave da composição de looks.

    Os 7 primeiros compõem o look "de rua". Os 4 últimos (hosiery, lingerie,
    sleepwear, beachwear) são grupos próprios que normalmente NÃO se misturam
    num look comum — separá-los facilita filtrar (ou excluir) na composição.
    """

    TOP = "top"                # blusa, camisa, regata, tricô
    BOTTOM = "bottom"          # calça, saia, shorts
    FULL_BODY = "full_body"    # vestido, macacão, macaquinho (ocupa o slot inteiro)
    OUTERWEAR = "outerwear"    # blazer, casaco, jaqueta, cardigã
    FOOTWEAR = "footwear"
    BAG = "bag"
    ACCESSORY = "accessory"    # cinto, joia, chapéu, óculos, cabelo...
    HOSIERY = "hosiery"        # meias, meia-calça
    LINGERIE = "lingerie"      # roupa íntima
    SLEEPWEAR = "sleepwear"    # pijama, camisola, robe
    BEACHWEAR = "beachwear"    # biquíni, maiô, saída de praia


class Subcategory(str, Enum):
    """Tipo específico da peça (vocabulário rico de moda feminina).

    Enum único e plano (melhor para o Gemini); a coerência com `category` é
    guiada pelo prompt. Agrupado por categoria apenas para leitura.
    """

    # --- top ---
    BLUSA = "blusa"
    CAMISA = "camisa"
    REGATA = "regata"
    CROPPED = "cropped"
    TRICO = "trico"
    SUETER = "sueter"
    BODY = "body"
    TSHIRT = "tshirt"
    BATA = "bata"
    POLO = "polo"
    TOP_FITNESS = "top_fitness"      # top de academia
    # --- bottom ---
    CALCA = "calca"
    JEANS = "jeans"
    CALCA_ALFAIATARIA = "calca_alfaiataria"
    PANTALONA = "pantalona"
    LEGGING = "legging"
    SAIA = "saia"
    SHORTS = "shorts"
    SAIA_SHORTS = "saia_shorts"
    BERMUDA = "bermuda"
    # --- full body ---
    VESTIDO = "vestido"
    MACACAO = "macacao"
    MACAQUINHO = "macaquinho"
    CONJUNTO = "conjunto"            # peças coordenadas (co-ord)
    # --- outerwear ---
    BLAZER = "blazer"
    CASACO = "casaco"
    SOBRETUDO = "sobretudo"
    JAQUETA = "jaqueta"
    TRENCH_COAT = "trench_coat"
    PARKA = "parka"
    CARDIGA = "cardiga"
    COLETE = "colete"
    KIMONO = "kimono"
    PONCHO = "poncho"
    # --- footwear ---
    SALTO = "salto"
    SCARPIN = "scarpin"
    RASTEIRA = "rasteira"
    SANDALIA = "sandalia"
    TENIS = "tenis"
    BOTA = "bota"
    ANKLE_BOOT = "ankle_boot"
    COTURNO = "coturno"
    MULE = "mule"
    SAPATILHA = "sapatilha"
    ANABELA = "anabela"             # salto plataforma/wedge
    MOCASSIM = "mocassim"
    TAMANCO = "tamanco"
    CHINELO = "chinelo"
    # --- bag ---
    BOLSA = "bolsa"
    TIRACOLO = "tiracolo"           # crossbody
    TOTE = "tote"
    CLUTCH = "clutch"
    POCHETE = "pochete"             # belt bag
    MOCHILA = "mochila"
    # --- accessory ---
    CINTO = "cinto"
    LENCO = "lenco"
    CHAPEU = "chapeu"
    BONE = "bone"
    GORRO = "gorro"
    OCULOS = "oculos"
    COLAR = "colar"
    BRINCO = "brinco"
    PULSEIRA = "pulseira"
    ANEL = "anel"
    RELOGIO = "relogio"
    LUVAS = "luvas"
    FAIXA_CABELO = "faixa_cabelo"
    BIJUTERIA = "bijuteria"
    # --- hosiery ---
    MEIA = "meia"
    MEIA_CALCA = "meia_calca"
    # --- lingerie ---
    SUTIA = "sutia"
    CALCINHA = "calcinha"
    SUTIA_ESPORTIVO = "sutia_esportivo"
    BODY_LINGERIE = "body_lingerie"
    CINTA = "cinta"
    CONJUNTO_LINGERIE = "conjunto_lingerie"
    # --- sleepwear ---
    PIJAMA = "pijama"
    CAMISOLA = "camisola"
    ROBE = "robe"
    SHORT_DOLL = "short_doll"
    # --- beachwear ---
    BIQUINI = "biquini"
    MAIO = "maio"
    SAIDA_DE_PRAIA = "saida_de_praia"
    CANGA = "canga"
    KAFTAN = "kaftan"
    # --- fallback ---
    OUTRO = "outro"


class ColorFamily(str, Enum):
    """Família de cor (não hex) — filtragem por cor para combinar looks."""

    PRETO = "preto"
    BRANCO = "branco"
    CINZA = "cinza"
    BEGE = "bege"
    MARROM = "marrom"
    VERMELHO = "vermelho"
    ROSA = "rosa"
    LARANJA = "laranja"
    AMARELO = "amarelo"
    VERDE = "verde"
    AZUL = "azul"
    ROXO = "roxo"
    DOURADO = "dourado"
    PRATEADO = "prateado"
    MULTICOR = "multicor"


class Shade(str, Enum):
    """Tom específico (refina a família) — só para display/busca; o motor de
    looks segue usando a família. Escolha o mais próximo; null se indefinido."""

    # pretos / cinzas
    PRETO = "preto"
    GRAFITE = "grafite"
    CHUMBO = "chumbo"
    CINZA_CLARO = "cinza_claro"
    CINZA_MESCLA = "cinza_mescla"
    # brancos / off
    BRANCO = "branco"
    OFF_WHITE = "off_white"
    GELO = "gelo"
    CRU = "cru"
    # beges / marrons
    BEGE = "bege"
    AREIA = "areia"
    NUDE = "nude"
    TAUPE = "taupe"
    CAMEL = "camel"
    CARAMELO = "caramelo"
    MARROM = "marrom"
    CHOCOLATE = "chocolate"
    CAFE = "cafe"
    # vermelhos / vinhos
    VERMELHO = "vermelho"
    CEREJA = "cereja"
    VINHO = "vinho"
    BORDO = "bordo"
    FERRUGEM = "ferrugem"
    # rosas
    ROSA = "rosa"
    ROSA_CLARO = "rosa_claro"
    ROSA_VELHO = "rosa_velho"
    SALMAO = "salmao"
    CORAL = "coral"
    PINK = "pink"
    FUCSIA = "fucsia"
    # laranjas / amarelos
    LARANJA = "laranja"
    TERRACOTA = "terracota"
    MOSTARDA = "mostarda"
    OCRE = "ocre"
    AMARELO = "amarelo"
    AMARELO_CLARO = "amarelo_claro"
    # verdes
    VERDE = "verde"
    VERDE_CLARO = "verde_claro"
    OLIVA = "oliva"
    MILITAR = "militar"
    SALVIA = "salvia"
    ESMERALDA = "esmeralda"
    VERDE_AGUA = "verde_agua"
    MENTA = "menta"
    PETROLEO = "petroleo"
    LIMAO = "limao"
    # azuis
    AZUL = "azul"
    MARINHO = "marinho"
    CELESTE = "celeste"
    ROYAL = "royal"
    TURQUESA = "turquesa"
    INDIGO = "indigo"
    JEANS_CLARO = "jeans_claro"
    # roxos
    ROXO = "roxo"
    LILAS = "lilas"
    LAVANDA = "lavanda"
    AMEIXA = "ameixa"
    UVA = "uva"
    # metais
    DOURADO = "dourado"
    BRONZE = "bronze"
    COBRE = "cobre"
    PRATEADO = "prateado"
    # genérico
    MULTICOR = "multicor"


class Pattern(str, Enum):
    LISO = "liso"
    LISTRADO = "listrado"
    FLORAL = "floral"
    XADREZ = "xadrez"
    POA = "poa"
    ANIMAL_PRINT = "animal_print"
    GEOMETRICO = "geometrico"
    ABSTRATO = "abstrato"
    ETNICO = "etnico"


class Material(str, Enum):
    ALGODAO = "algodao"
    JEANS = "jeans"
    LINHO = "linho"
    SEDA = "seda"
    MALHA = "malha"
    TRICO = "trico"
    COURO = "couro"
    COURO_SINTETICO = "couro_sintetico"
    LA = "la"
    POLIESTER = "poliester"
    RENDA = "renda"
    CETIM = "cetim"
    VELUDO = "veludo"
    LYCRA = "lycra"          # moda praia / fitness
    VISCOSE = "viscose"
    CASHMERE = "cashmere"
    MOHAIR = "mohair"
    TWEED = "tweed"
    CROCHE = "croche"
    MOLETOM = "moletom"
    SARJA = "sarja"
    NYLON = "nylon"
    OUTRO = "outro"


class Length(str, Enum):
    """Comprimento da barra (aplica a full_body e bottom)."""

    CROPPED = "cropped"
    CINTURA = "cintura"
    MINI = "mini"
    ACIMA_JOELHO = "acima_joelho"
    JOELHO = "joelho"
    MIDI = "midi"
    MAXI = "maxi"
    CHAO = "chao"


class SleeveLength(str, Enum):
    SEM_MANGA = "sem_manga"
    ALCINHA = "alcinha"
    CURTA = "curta"
    TRES_QUARTOS = "tres_quartos"
    LONGA = "longa"


class Neckline(str, Enum):
    REDONDA = "redonda"
    V = "v"
    CANOA = "canoa"
    GOLA_ALTA = "gola_alta"
    OMBRO_A_OMBRO = "ombro_a_ombro"
    TOMARA_QUE_CAIA = "tomara_que_caia"
    FRENTE_UNICA = "frente_unica"
    POLO = "polo"
    DECOTE_NADADOR = "nadador"


class Fit(str, Enum):
    JUSTO = "justo"
    REGULAR = "regular"
    SOLTO = "solto"
    OVERSIZED = "oversized"
    EVASE = "evase"          # A-line / godê
    RETO = "reto"


class Formality(str, Enum):
    """CRÍTICO para a coerência do look — não se mistura academia com gala."""

    CASUAL = "casual"
    SMART_CASUAL = "smart_casual"
    TRABALHO = "trabalho"
    COCKTAIL = "cocktail"
    GALA = "gala"


class HeelHeight(str, Enum):
    """Só calçados."""

    RASO = "raso"
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    PLATAFORMA = "plataforma"


class Season(str, Enum):
    PRIMAVERA = "primavera"
    VERAO = "verao"
    OUTONO = "outono"
    INVERNO = "inverno"


class StyleAesthetic(str, Enum):
    CLASSICO = "classico"
    MINIMALISTA = "minimalista"
    BOHO = "boho"
    ROMANTICO = "romantico"
    ESPORTIVO = "esportivo"
    STREETWEAR = "streetwear"
    SEXY = "sexy"
    VINTAGE = "vintage"
    SOFISTICADO = "sofisticado"


class Occasion(str, Enum):
    DIA_A_DIA = "dia_a_dia"
    TRABALHO = "trabalho"
    ALMOCO_AMIGAS = "almoco_amigas"   # almoço com amigas (casual-chic diurno)
    JANTAR = "jantar"                 # jantar (noite, mais arrumado)
    ANIVERSARIO_INFANTIL = "aniversario_infantil"  # festinha de criança (prático+estiloso)
    FESTA = "festa"
    CASAMENTO = "casamento"
    PRAIA = "praia"
    ACADEMIA = "academia"
    VIAGEM = "viagem"
    ENCONTRO = "encontro"   # legado (peças antigas já marcadas); fora do seletor de looks
    CASA = "casa"            # lounge / dormir


# --------------------------------------------------------------------------- #
# Modelo de extração
# --------------------------------------------------------------------------- #
class GarmentMetadata(BaseModel):
    """
    Metadados estruturados de uma peça. A ordem dos campos é deliberada
    (do mais determinante ao menos) para guiar o raciocínio do modelo.
    """

    # guard-rails primeiro
    is_garment: bool = Field(
        description="true se a imagem mostra uma peça de roupa, calçado ou acessório; "
        "false caso contrário (pessoa sem foco na roupa, paisagem, objeto aleatório)."
    )
    extraction_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confiança geral (0 a 1) na qualidade desta extração.",
    )

    # categorização (chave da composição)
    category: Category = Field(description="O slot que a peça ocupa no corpo.")
    subcategory: Subcategory = Field(description="O tipo específico da peça.")

    # cor e estampa
    primary_color: ColorFamily = Field(description="Família de cor predominante.")
    shade: Optional[Shade] = Field(
        default=None,
        description="Tom específico que refina a família (ex.: azul->marinho, "
        "laranja->terracota, vermelho->vinho). Escolha o mais próximo; null se indefinido.",
    )
    secondary_colors: list[ColorFamily] = Field(
        default_factory=list, description="Outras cores presentes."
    )
    pattern: Pattern = Field(default=Pattern.LISO, description="Estampa/padrão.")
    material: Optional[Material] = Field(
        default=None, description="Material aparente, se identificável."
    )

    # styling / filtros de composição
    formality: Formality = Field(description="Nível de formalidade da peça.")
    seasons: list[Season] = Field(
        default_factory=list, description="Estações adequadas."
    )
    style_aesthetics: list[StyleAesthetic] = Field(
        default_factory=list, description="Estéticas/vibe da peça."
    )
    occasions: list[Occasion] = Field(
        default_factory=list, description="Ocasiões de uso."
    )

    # condicionais — null quando não se aplicam à categoria
    length: Optional[Length] = Field(
        default=None, description="Comprimento da barra (full_body/bottom)."
    )
    sleeve_length: Optional[SleeveLength] = Field(
        default=None, description="Comprimento da manga (top/full_body/outerwear)."
    )
    neckline: Optional[Neckline] = Field(
        default=None, description="Decote/gola (top/full_body)."
    )
    fit: Optional[Fit] = Field(default=None, description="Caimento/modelagem.")
    heel_height: Optional[HeelHeight] = Field(
        default=None, description="Altura do salto (apenas footwear)."
    )

    # identificação — preenchidos pela IA SÓ quando claramente visíveis
    # (logo, etiqueta, estampa de marca); senão null, para preenchimento manual.
    brand: Optional[str] = Field(
        default=None,
        description="Marca, apenas se houver logo/etiqueta/estampa de marca legível. "
        "Não chute a marca; deixe null se não estiver visível.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Nome/modelo da peça (coleção, referência), apenas se visível. "
        "Não invente; deixe null se não houver.",
    )

    # texto livre (alimenta busca semântica/embeddings depois)
    description: str = Field(
        description="Uma frase natural descrevendo a peça, como uma consultora de moda."
    )
    style_keywords: list[str] = Field(
        default_factory=list, description="Palavras-chave livres de estilo."
    )


# Colunas promovidas a campos no Postgres (filtro de composição + identificação).
PROMOTED_COLUMNS = (
    "category",
    "subcategory",
    "primary_color",
    "pattern",
    "material",
    "formality",
    "length",
    "seasons",
    "style_aesthetics",
    "occasions",
    "brand",
    "model_name",
)
