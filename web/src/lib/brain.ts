import "server-only";

export type LookPiece = {
  id: string;
  category: string;
  subcategory: string | null;
  primary_color: string | null;
  brand: string | null;
  description: string | null;
};

export type LookResult = {
  look_id: string | null;
  model_image: string | null;
  occasion: string | null;
  season: string | null;
  temperature: string | null;
  boldness: string | null;
  rationale: string | null;
  missing: string[];
  cold_without_coat: boolean;
  pieces: LookPiece[];
};

export type SearchResult = {
  query: string;
  results: (LookPiece & { similarity: number })[];
};

export type SimilarResult = {
  id: string;
  results: (LookPiece & { similarity: number })[];
};

export type CapsuleLook = {
  label: string;
  occasion: string | null;
  pieces: LookPiece[];
  missing: string[];
};

export type CapsuleResult = {
  days: number;
  occasion: string | null;
  night: string | null;
  season: string | null;
  total: number;
  groups: { category: string; pieces: LookPiece[] }[];
  looks: CapsuleLook[];
};

function brainUrl(path: string, params: Record<string, string | undefined>): URL {
  const base = process.env.BRAIN_URL;
  if (!base) throw new Error("BRAIN_URL ausente no ambiente.");
  const url = new URL(path, base);
  for (const [k, v] of Object.entries(params)) {
    if (v) url.searchParams.set(k, v);
  }
  return url;
}

async function brainFetch<T>(url: URL): Promise<T> {
  const res = await fetch(url, {
    headers: { "X-Brain-Secret": process.env.BRAIN_SECRET ?? "" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Cérebro respondeu ${res.status}`);
  return res.json() as Promise<T>;
}

export function composeLook(
  occasion?: string,
  season?: string,
  temp?: string,
  bold?: string,
): Promise<LookResult> {
  return brainFetch<LookResult>(
    brainUrl("/api/look", { occasion, season, temp, bold }),
  );
}

export function searchGarments(q: string, k = 12): Promise<SearchResult> {
  return brainFetch<SearchResult>(brainUrl("/api/search", { q, k: String(k) }));
}

export function similarGarments(id: string, k = 6): Promise<SimilarResult> {
  return brainFetch<SimilarResult>(brainUrl("/api/similar", { id, k: String(k) }));
}

export function packCapsule(
  days?: string,
  occasion?: string,
  night?: string,
  season?: string,
): Promise<CapsuleResult> {
  return brainFetch<CapsuleResult>(
    brainUrl("/api/capsule", { days, occasion, night, season }),
  );
}
