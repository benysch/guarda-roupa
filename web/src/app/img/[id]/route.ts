import { getImageBytes } from "@/lib/wardrobe";

// Proxy de imagem: baixa do bucket privado com a service key e serve os bytes.
// URL estável (cacheável) e sem expor URL assinada/token ao navegador.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  // só ids no formato uuid — evita path traversal
  if (!/^[0-9a-fA-F-]{36}$/.test(id)) {
    return new Response("bad id", { status: 400 });
  }
  const bytes = await getImageBytes(id);
  if (!bytes) return new Response("não encontrada", { status: 404 });
  return new Response(bytes as unknown as BodyInit, {
    headers: {
      "Content-Type": "image/jpeg",
      "Cache-Control": "private, max-age=3600",
    },
  });
}
