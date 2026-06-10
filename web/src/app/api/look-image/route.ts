// Repassa o pedido de imagem do look ao cérebro Python (com o segredo) e
// devolve o PNG ao navegador. Protegido pelo proxy (cookie de sessão).
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(req: Request) {
  const url = new URL(req.url);
  const ids = url.searchParams.get("ids") ?? "";
  const occasion = url.searchParams.get("occasion") ?? "";
  const season = url.searchParams.get("season") ?? "";

  const base = process.env.BRAIN_URL;
  if (!base || !ids) {
    return Response.json({ error: "bad-request" }, { status: 400 });
  }

  const target = new URL("/api/look-image", base);
  target.searchParams.set("ids", ids);
  if (occasion) target.searchParams.set("occasion", occasion);
  if (season) target.searchParams.set("season", season);

  const res = await fetch(target, {
    headers: { "X-Brain-Secret": process.env.BRAIN_SECRET ?? "" },
    cache: "no-store",
  });

  const ct = res.headers.get("content-type") ?? "";
  if (res.ok && ct.startsWith("image/")) {
    return new Response(await res.arrayBuffer(), {
      headers: { "Content-Type": "image/png", "Cache-Control": "no-store" },
    });
  }

  const body = await res.json().catch(() => ({ error: "falha" }));
  return Response.json(body, { status: res.status });
}
