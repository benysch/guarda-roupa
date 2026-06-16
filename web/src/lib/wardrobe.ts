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
  cutout_status: "pending" | "approved" | "rejected" | null;
  status: string;
  created_at: string;
};

const COLUMNS =
  "id,category,subcategory,primary_color,material,pattern,formality,brand,model_name,description,seasons,occasions,image_path,cutout_status,status,created_at";

/** URL da rota /img a usar: recorte aprovado quando houver, senão a original. */
export function imageSrc(g: Pick<Garment, "id" | "cutout_status">): string {
  return g.cutout_status === "approved"
    ? `/img/${g.id}?v=cutout`
    : `/img/${g.id}`;
}

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

/** Peças cruas (subidas só como foto) aguardando classificação manual. */
export async function listUnclassified(): Promise<Garment[]> {
  const sb = supabaseAdmin();
  const { data, error } = await sb
    .from("garments")
    .select(COLUMNS)
    .eq("status", "needs_review")
    .order("created_at", { ascending: true });
  if (error) throw error;
  return (data ?? []) as Garment[];
}

export async function countUnclassified(): Promise<number> {
  const sb = supabaseAdmin();
  const { count, error } = await sb
    .from("garments")
    .select("id", { count: "exact", head: true })
    .eq("status", "needs_review");
  if (error) throw error;
  return count ?? 0;
}

export async function getGarment(id: string): Promise<Garment | null> {
  const sb = supabaseAdmin();
  const { data, error } = await sb
    .from("garments")
    .select(COLUMNS)
    .eq("id", id)
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return (data as Garment | null) ?? null;
}

const EDITABLE = [
  "category",
  "primary_color",
  "pattern",
  "material",
  "brand",
  "model_name",
] as const;

export async function updateGarment(
  id: string,
  fields: Record<string, string | null>,
): Promise<void> {
  const sb = supabaseAdmin();
  const clean: Record<string, string | null> = {};
  for (const k of EDITABLE) {
    if (k in fields) clean[k] = fields[k] === "" ? null : fields[k];
  }
  const { error } = await sb.from("garments").update(clean).eq("id", id);
  if (error) throw error;
}

/** Classifica uma peça crua: grava os campos e a promove a 'processed' (entra no acervo). */
export async function classifyGarment(
  id: string,
  fields: Record<string, string | null>,
): Promise<void> {
  const sb = supabaseAdmin();
  const clean: Record<string, string | null> = {};
  for (const k of EDITABLE) {
    if (k in fields) clean[k] = fields[k] === "" ? null : fields[k];
  }
  clean.status = "processed";
  const { error } = await sb.from("garments").update(clean).eq("id", id);
  if (error) throw error;
}

export async function deleteGarment(id: string): Promise<void> {
  const sb = supabaseAdmin();
  // remove os objetos do Storage (original + recorte) antes de apagar a linha
  await sb.storage.from(BUCKET).remove([`${id}.jpg`, `${id}_cutout.png`]);
  const { error } = await sb.from("garments").delete().eq("id", id);
  if (error) throw error;
}

/** Aprova o recorte (passa a ser exibido) ou o rejeita (apaga o arquivo, mantém original). */
export async function setCutoutStatus(
  id: string,
  status: "approved" | "rejected",
): Promise<void> {
  const sb = supabaseAdmin();
  if (status === "rejected") {
    await sb.storage.from(BUCKET).remove([`${id}_cutout.png`]);
  }
  const { error } = await sb
    .from("garments")
    .update({ cutout_status: status })
    .eq("id", id);
  if (error) throw error;
}

/** Baixa os bytes da imagem do bucket privado (servida pela rota /img/[id]). */
export async function getImageBytes(
  garmentId: string,
  variant: "original" | "cutout" = "original",
): Promise<Uint8Array | null> {
  const sb = supabaseAdmin();
  const object =
    variant === "cutout" ? `${garmentId}_cutout.png` : `${garmentId}.jpg`;
  const { data, error } = await sb.storage.from(BUCKET).download(object);
  if (error || !data) return null;
  return new Uint8Array(await data.arrayBuffer());
}

/** Foto (PNG) da modelo vestindo um look curado: objeto `look_<id>.png` no bucket. */
export async function getLookImageBytes(
  lookId: string,
): Promise<Uint8Array | null> {
  const sb = supabaseAdmin();
  const { data, error } = await sb.storage
    .from(BUCKET)
    .download(`look_${lookId}.png`);
  if (error || !data) return null;
  return new Uint8Array(await data.arrayBuffer());
}
