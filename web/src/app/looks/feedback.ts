"use server";

import { supabaseAdmin } from "@/lib/supabase";
import type { LookResult } from "@/lib/brain";

export type Verdict = "gostei" | "nao_gostei";

/**
 * Registra o gostei/não gostei de uma composição. O 👎 também marca o look
 * curado como `suppressed` (some na hora dos próximos sorteios). O acúmulo
 * vira sinal pra recalibrar o estilista offline (skill + regeneração).
 */
export async function rateLook(
  look: Pick<
    LookResult,
    | "look_id"
    | "occasion"
    | "season"
    | "temperature"
    | "boldness"
    | "rationale"
    | "pieces"
  >,
  verdict: Verdict,
): Promise<{ ok: boolean }> {
  const db = supabaseAdmin();

  const { error } = await db.from("look_feedback").insert({
    curated_look_id: look.look_id,
    garment_ids: look.pieces.map((p) => p.id),
    occasion: look.occasion,
    season: look.season,
    temperature: look.temperature,
    boldness: look.boldness,
    rationale: look.rationale,
    verdict,
  });
  if (error) return { ok: false };

  // 👎 num look curado -> esconde já dos próximos sorteios.
  if (verdict === "nao_gostei" && look.look_id) {
    await db
      .from("curated_looks")
      .update({ suppressed: true })
      .eq("id", look.look_id);
  }

  return { ok: true };
}
