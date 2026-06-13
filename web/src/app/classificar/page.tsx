import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { imageSrc, listUnclassified } from "@/lib/wardrobe";

export const dynamic = "force-dynamic";

export default async function Classificar() {
  const garments = await listUnclassified();

  return (
    <>
      <SiteHeader active="/classificar" />
      <main className="mx-auto max-w-6xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            {garments.length}{" "}
            {garments.length === 1 ? "foto" : "fotos"} aguardando
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            A Classificar
          </h1>
          <p className="mt-4 max-w-xl text-sm text-muted-foreground">
            Fotos que você mandou pelo bot. Toque em cada uma para preencher
            categoria, cor e detalhes — ao classificar, a peça entra no acervo.
          </p>
        </section>

        {garments.length === 0 ? (
          <p className="py-24 text-center text-muted-foreground">
            Nada para classificar. Mande fotos pelo bot do Telegram. 📸
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-x-5 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
            {garments.map((g) => (
              <Link key={g.id} href={`/peca/${g.id}`} className="group block">
                <div className="relative aspect-[3/4] overflow-hidden bg-muted">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageSrc(g)}
                    alt="Peça a classificar"
                    loading="lazy"
                    className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.05]"
                  />
                  <span className="tracking-label absolute left-2 top-2 rounded-full bg-background/85 px-2.5 py-1 text-[10px] uppercase text-foreground backdrop-blur-sm">
                    Classificar →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
