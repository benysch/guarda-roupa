import "server-only";
import { createClient } from "@supabase/supabase-js";

/**
 * Cliente Supabase com a SERVICE KEY — somente servidor (RSC / route handlers /
 * server actions). O navegador nunca recebe esta chave nem fala com o Supabase
 * direto; toda leitura passa por aqui, atrás da autenticação. Isso mantém a
 * decisão de RLS desligada segura para um site público.
 */
export function supabaseAdmin() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_URL / SUPABASE_SERVICE_KEY ausentes no ambiente.");
  }
  return createClient(url, key, { auth: { persistSession: false } });
}

export const BUCKET = process.env.SUPABASE_BUCKET || "wardrobe";
