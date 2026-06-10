import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { similarGarments, type SimilarResult } from "@/lib/brain";
import { titleCase } from "@/lib/labels";
import { getGarment } from "@/lib/wardrobe";
import { EditForm } from "./edit-form";

export const dynamic = "force-dynamic";

export default async function GarmentPage(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  const g = await getGarment(id);
  if (!g) notFound();

  let similar: SimilarResult | null = null;
  try {
    similar = await similarGarments(id, 6);
  } catch {
    similar = null;
  }

  return (
    <>
      <SiteHeader active="/" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <div className="py-6">
          <Link
            href="/"
            className="tracking-label text-[11px] uppercase text-muted-foreground transition-colors hover:text-foreground"
          >
            ← Acervo
          </Link>
        </div>

        <div className="grid gap-10 md:grid-cols-2">
          <div className="relative aspect-[3/4] overflow-hidden bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/img/${g.id}`}
              alt={g.description ?? g.category}
              className="h-full w-full object-cover"
            />
          </div>
          <EditForm g={g} />
        </div>

        {similar && similar.results.length > 0 && (
          <section className="mt-16 border-t border-border pt-10">
            <p className="tracking-label mb-6 text-[11px] uppercase text-muted-foreground">
              Peças parecidas
            </p>
            <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
              {similar.results.map((r) => (
                <Link key={r.id} href={`/peca/${r.id}`} className="group block">
                  <div className="relative aspect-[3/4] overflow-hidden bg-muted">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/img/${r.id}`}
                      alt={r.description ?? r.category}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.05]"
                    />
                  </div>
                  <p className="mt-2 truncate text-[11px] text-muted-foreground">
                    {titleCase(r.subcategory ?? r.category)}
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
