import { getLookImageBytes } from "@/lib/wardrobe";

// Serve a foto (PNG) da modelo vestindo um look curado, do bucket privado.
// URL estável (cacheável) a partir do id do look.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  if (!/^[0-9a-fA-F-]{36}$/.test(id)) {
    return new Response("bad id", { status: 400 });
  }
  const bytes = await getLookImageBytes(id);
  if (!bytes) return new Response("não encontrada", { status: 404 });
  return new Response(bytes as unknown as BodyInit, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "private, max-age=3600",
    },
  });
}
