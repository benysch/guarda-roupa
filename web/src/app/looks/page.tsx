import { SiteHeader } from "@/components/site-header";
import { composeLook, type LookResult } from "@/lib/brain";
import { titleCase } from "@/lib/labels";
import { LookControls } from "./look-controls";

export const dynamic = "force-dynamic";
// o estilista (Gemini) pode levar ~10-25s; dá folga à função
export const maxDuration = 60;

const MISSING_LABEL: Record<string, string> = {
  top: "um top",
  bottom: "uma calça ou saia",
  footwear: "um calçado",
  full_body: "um vestido/macacão",
};

export default async function LooksPage(props: {
  searchParams: Promise<{ occasion?: string; season?: string; r?: string }>;
}) {
  const sp = await props.searchParams;
  const requested = Boolean(sp.occasion || sp.season || sp.r);
  const look = requested ? await composeLook(sp.occasion, sp.season) : null;

  return (
    <>
      <SiteHeader active="/looks" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Estilista · paleta inverno frio
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Montar Look
          </h1>
        </section>

        <LookControls
          occasion={sp.occasion ?? ""}
          season={sp.season ?? ""}
          hasLook={!!look}
        />

        <div className="mt-12">
          {look ? <LookView look={look} /> : <EmptyState />}
        </div>
      </main>
    </>
  );
}

function EmptyState() {
  return (
    <div className="border-t border-border py-24 text-center">
      <p className="font-display text-2xl italic text-muted-foreground">
        Escolha uma ocasião e a estação — o estilista monta o look.
      </p>
    </div>
  );
}

function LookView({ look }: { look: LookResult }) {
  if (look.pieces.length === 0) {
    return (
      <div className="border-t border-border py-24 text-center text-muted-foreground">
        Ainda não tenho peças suficientes pra montar um look. Cadastre mais pelo
        bot. 📸
      </div>
    );
  }

  const title = look.occasion
    ? `Look ${look.occasion.replace(/_/g, " ")}`
    : "Seu look";

  return (
    <article className="border-t border-border pt-10 fade-up">
      <header className="mb-8 flex items-baseline justify-between gap-4">
        <h2 className="font-display text-3xl tracking-tight capitalize">
          {title}
        </h2>
        {look.season && (
          <span className="tracking-label text-[11px] uppercase text-muted-foreground">
            {look.season}
          </span>
        )}
      </header>

      <div className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
        {look.pieces.map((p, i) => (
          <figure
            key={p.id}
            className="fade-up"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <div className="relative aspect-[3/4] overflow-hidden bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/img/${p.id}`}
                alt={p.description ?? p.category}
                className="h-full w-full object-cover"
              />
            </div>
            <figcaption className="mt-3">
              <p className="font-display text-base leading-tight">
                {titleCase(p.subcategory ?? p.category)}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {[titleCase(p.primary_color), p.brand]
                  .filter(Boolean)
                  .join(" · ") || "—"}
              </p>
            </figcaption>
          </figure>
        ))}
      </div>

      {look.rationale && (
        <blockquote className="mt-12 border-l-2 border-primary pl-6">
          <p className="font-display text-xl italic leading-relaxed text-foreground/90">
            {look.rationale}
          </p>
          <footer className="tracking-label mt-3 text-[10px] uppercase text-muted-foreground">
            — a estilista
          </footer>
        </blockquote>
      )}

      {look.missing.length > 0 && (
        <p className="mt-8 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
          ⚠️ Faltou{" "}
          {look.missing.map((m) => MISSING_LABEL[m] ?? m).join(", ")} pra
          completar o look. Cadastre essas peças pelo bot.
        </p>
      )}
    </article>
  );
}
