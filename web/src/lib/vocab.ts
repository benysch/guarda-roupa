// Vocabulário fechado (espelha wardrobe/schema.py) — usado nos formulários de
// edição do site. São listas de opções; a fonte da verdade do schema é o Python.

export const COLORS: string[] = [
  "preto",
  "branco",
  "cinza",
  "bege",
  "marrom",
  "vermelho",
  "rosa",
  "laranja",
  "amarelo",
  "verde",
  "azul",
  "roxo",
  "dourado",
  "prateado",
  "multicor",
];

// Tons (refina a família). Agrupados por família pra o form mostrar só os
// relevantes. Espelha o enum Shade em wardrobe/schema.py.
export const SHADES_BY_FAMILY: Record<string, [string, string][]> = {
  preto: [["preto", "Preto"], ["grafite", "Grafite"], ["chumbo", "Chumbo"]],
  branco: [["branco", "Branco"], ["off_white", "Off-white"], ["gelo", "Gelo"], ["cru", "Cru"]],
  cinza: [["cinza_claro", "Cinza-claro"], ["cinza_mescla", "Cinza-mescla"], ["chumbo", "Chumbo"]],
  bege: [["bege", "Bege"], ["areia", "Areia"], ["nude", "Nude"], ["taupe", "Taupe"], ["camel", "Camel"]],
  marrom: [["marrom", "Marrom"], ["caramelo", "Caramelo"], ["chocolate", "Chocolate"], ["cafe", "Café"], ["camel", "Camel"]],
  vermelho: [["vermelho", "Vermelho"], ["cereja", "Cereja"], ["vinho", "Vinho"], ["bordo", "Bordô"], ["ferrugem", "Ferrugem"]],
  rosa: [["rosa", "Rosa"], ["rosa_claro", "Rosa-claro"], ["rosa_velho", "Rosa-velho"], ["salmao", "Salmão"], ["coral", "Coral"], ["pink", "Pink"], ["fucsia", "Fúcsia"]],
  laranja: [["laranja", "Laranja"], ["terracota", "Terracota"], ["ferrugem", "Ferrugem"], ["coral", "Coral"]],
  amarelo: [["amarelo", "Amarelo"], ["amarelo_claro", "Amarelo-claro"], ["mostarda", "Mostarda"], ["ocre", "Ocre"]],
  verde: [["verde", "Verde"], ["verde_claro", "Verde-claro"], ["oliva", "Oliva"], ["militar", "Militar"], ["salvia", "Sálvia"], ["esmeralda", "Esmeralda"], ["verde_agua", "Verde-água"], ["menta", "Menta"], ["petroleo", "Petróleo"], ["limao", "Limão"]],
  azul: [["azul", "Azul"], ["marinho", "Marinho"], ["celeste", "Celeste"], ["royal", "Royal"], ["turquesa", "Turquesa"], ["indigo", "Índigo"], ["jeans_claro", "Jeans-claro"], ["petroleo", "Petróleo"]],
  roxo: [["roxo", "Roxo"], ["lilas", "Lilás"], ["lavanda", "Lavanda"], ["ameixa", "Ameixa"], ["uva", "Uva"]],
  dourado: [["dourado", "Dourado"], ["bronze", "Bronze"], ["cobre", "Cobre"]],
  prateado: [["prateado", "Prateado"], ["grafite", "Grafite"]],
  multicor: [["multicor", "Multicor"]],
};

export const PATTERNS: [string, string][] = [
  ["liso", "Liso"],
  ["listrado", "Listrado"],
  ["floral", "Floral"],
  ["xadrez", "Xadrez"],
  ["poa", "Poá"],
  ["animal_print", "Animal print"],
  ["geometrico", "Geométrico"],
  ["abstrato", "Abstrato"],
  ["etnico", "Étnico"],
];

export const MATERIALS: [string, string][] = [
  ["algodao", "Algodão"],
  ["jeans", "Jeans"],
  ["linho", "Linho"],
  ["seda", "Seda"],
  ["malha", "Malha"],
  ["trico", "Tricô"],
  ["couro", "Couro"],
  ["couro_sintetico", "Couro sintético"],
  ["la", "Lã"],
  ["poliester", "Poliéster"],
  ["renda", "Renda"],
  ["cetim", "Cetim"],
  ["veludo", "Veludo"],
  ["lycra", "Lycra"],
  ["viscose", "Viscose"],
  ["cashmere", "Cashmere"],
  ["mohair", "Mohair"],
  ["tweed", "Tweed"],
  ["croche", "Crochê"],
  ["moletom", "Moletom"],
  ["sarja", "Sarja"],
  ["nylon", "Nylon"],
  ["outro", "Outro"],
];
