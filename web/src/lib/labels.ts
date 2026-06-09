export const CATEGORY_LABELS: Record<string, string> = {
  top: "Tops",
  bottom: "Partes de baixo",
  full_body: "Vestidos & macacões",
  outerwear: "Casacos",
  footwear: "Calçados",
  bag: "Bolsas",
  accessory: "Acessórios",
  hosiery: "Meias",
  lingerie: "Lingerie",
  sleepwear: "Pijamas",
  beachwear: "Praia",
};

export const CATEGORY_ORDER = [
  "top",
  "bottom",
  "full_body",
  "outerwear",
  "footwear",
  "bag",
  "accessory",
  "hosiery",
  "lingerie",
  "sleepwear",
  "beachwear",
];

/** Família de cor -> hex aproximado, só para a bolinha de cor nos cards. */
export const COLOR_HEX: Record<string, string> = {
  preto: "#17171a",
  branco: "#f4f4f2",
  cinza: "#9aa0a6",
  bege: "#d9c9a8",
  marrom: "#6b4a2b",
  vermelho: "#b3122e",
  rosa: "#e8669e",
  laranja: "#e8772e",
  amarelo: "#e8c64a",
  verde: "#2f7d52",
  azul: "#2f5d91",
  roxo: "#6b3fa0",
  dourado: "#c2a14a",
  prateado: "#bfc4c9",
  multicor: "#9b8fae",
};

export function titleCase(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}
