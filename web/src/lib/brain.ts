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
  occasion: string | null;
  season: string | null;
  rationale: string | null;
  missing: string[];
  pieces: LookPiece[];
};

export type SearchResult = {
  query: string;
  results: (LookPiece & { similarity: number })[];
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
): Promise<LookResult> {
  return brainFetch<LookResult>(brainUrl("/api/look", { occasion, season }));
}

export function searchGarments(q: string, k = 12): Promise<SearchResult> {
  return brainFetch<SearchResult>(brainUrl("/api/search", { q, k: String(k) }));
}
