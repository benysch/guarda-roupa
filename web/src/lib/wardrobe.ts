import "server-only";
import { BUCKET, supabaseAdmin } from "./supabase";

export type Garment = {
  id: string;
  category: string;
  subcategory: string | null;
  primary_color: string | null;
  material: string | null;
  pattern: string | null;
  formality: string | null;
  brand: string | null;
  model_name: string | null;
  description: string | null;
  seasons: string[] | null;
  occasions: string[] | null;
  image_path: string;
  created_at: string;
};

const COLUMNS =
  "id,category,subcategory,primary_color,material,pattern,formality,brand,model_name,description,seasons,occasions,image_path,created_at";

export async function listGarments(category?: string): Promise<Garment[]> {
  const sb = supabaseAdmin();
  let q = sb
    .from("garments")
    .select(COLUMNS)
    .eq("status", "processed")
    .order("created_at", { ascending: false });
  if (category && category !== "todos") q = q.eq("category", category);
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Garment[];
}

export async function categoryCounts(): Promise<Record<string, number>> {
  const sb = supabaseAdmin();
  const { data, error } = await sb
    .from("garments")
    .select("category")
    .eq("status", "processed");
  if (error) throw error;
  const counts: Record<string, number> = {};
  for (const r of data ?? []) {
    const c = (r as { category: string }).category;
    counts[c] = (counts[c] ?? 0) + 1;
  }
  return counts;
}

/** Baixa os bytes da imagem do bucket privado (servida pela rota /img/[id]). */
export async function getImageBytes(
  garmentId: string,
): Promise<Uint8Array | null> {
  const sb = supabaseAdmin();
  const { data, error } = await sb.storage
    .from(BUCKET)
    .download(`${garmentId}.jpg`);
  if (error || !data) return null;
  return new Uint8Array(await data.arrayBuffer());
}
