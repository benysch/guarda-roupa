import { SiteHeader } from "@/components/site-header";
import { searchGarments, type SearchResult } from "@/lib/brain";
import { COLOR_HEX, titleCase } from "@/lib/labels";
import { SearchBox } from "./search-box";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

export default async function BuscarPage(props: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await props.searchParams;
  const query = (q ?? "").trim();
  const data: SearchResult | null = query
    ? await searchGarments(query, 12)
    : null;

  return (
    <>
      <SiteHeader active="/buscar" />
      <main className="mx-auto max-w-6xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Busca por descrição · semântica
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Buscar
          </h1>
        </section>

        <SearchBox initial={query} />

        <div className="mt-12">
          {data ? <Results data={data} /> : <EmptyState />}
        </div>
      </main>
    </>
  );
}

function EmptyState() {
  return (
    <div className="border-t border-border py-24 text-center">
      <p className="font-display text-2xl italic text-muted-foreground">
        Descreva o que procura — eu acho pelas características, não por palavra
        exata.
      </p>
    </div>
  );
}

function Results({ data }: { data: SearchResult }) {
  if (data.results.length === 0) {
    return (
      <div className="border-t border-border py-24 text-center text-muted-foreground">
        Nada parecido com{" "}
        <span className="text-foreground">“{data.query}”</span> no guarda-roupa.
      </div>
    );
  }

  return (
    <section className="border-t border-border pt-8 fade-up">
      <p className="tracking-label mb-8 text-[11px] uppercase text-muted-foreground">
        Resultados para “{data.query}”
      </p>
      <div className="grid grid-cols-2 gap-x-5 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
        {data.results.map((r, i) => (
          <article
            key={r.id}
            className="group fade-up"
            style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}
          >
            <div className="relative aspect-[3/4] overflow-hidden bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/img/${r.id}`}
                alt={r.description ?? r.category}
                loading="lazy"
                className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
              />
              <span className="tracking-label absolute left-2 top-2 rounded-full bg-background/85 px-2 py-0.5 text-[10px] uppercase text-foreground backdrop-blur-sm">
                {Math.round((r.similarity ?? 0) * 100)}%
              </span>
            </div>
            <div className="mt-3 flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="font-display truncate text-base leading-tight">
                  {titleCase(r.subcategory ?? r.category)}
                </h3>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {[titleCase(r.primary_color), r.brand]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </p>
              </div>
              {r.primary_color && (
                <span
                  className="mt-1 h-3 w-3 shrink-0 rounded-full ring-1 ring-border"
                  style={{
                    backgroundColor: COLOR_HEX[r.primary_color] ?? "#ccc",
                  }}
                />
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
