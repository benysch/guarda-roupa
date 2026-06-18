import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { packCapsule, type CapsuleLook, type CapsuleResult } from "@/lib/brain";
import { CATEGORY_LABELS, titleCase } from "@/lib/labels";
import { CapsuleControls } from "./capsule-controls";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const MISSING_LABEL: Record<string, string> = {
  top: "um top",
  bottom: "uma calça ou saia",
  footwear: "um calçado",
  full_body: "um vestido/macacão",
};

export default async function MalaPage(props: {
  searchParams: Promise<{
    days?: string;
    occasion?: string;
    night?: string;
    season?: string;
  }>;
}) {
  const sp = await props.searchParams;
  const requested = Boolean(sp.days || sp.occasion || sp.night || sp.season);
  const capsule = requested
    ? await packCapsule(sp.days, sp.occasion, sp.night, sp.season)
    : null;

  return (
    <>
      <SiteHeader active="/mala" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Cápsula mínima · estilo livre
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Mala de Viagem
          </h1>
        </section>

        <CapsuleControls
          days={sp.days ?? ""}
          occasion={sp.occasion ?? ""}
          night={sp.night ?? ""}
          season={sp.season ?? ""}
          hasCapsule={!!capsule}
        />

        <div className="mt-12">
          {capsule ? <CapsuleView capsule={capsule} /> : <EmptyState />}
        </div>
      </main>
    </>
  );
}

function EmptyState() {
  return (
    <div className="border-t border-border py-24 text-center">
      <p className="font-display text-2xl italic text-muted-foreground">
        Conte da viagem — eu monto a menor mala que cobre todos os dias.
      </p>
    </div>
  );
}

function CapsuleView({ capsule }: { capsule: CapsuleResult }) {
  if (capsule.total === 0) {
    return (
      <div className="border-t border-border py-24 text-center text-muted-foreground">
        Ainda não tenho peças suficientes pra essa viagem. Cadastre mais pelo
        bot. 📸
      </div>
    );
  }

  const uncovered = capsule.looks.filter((l) => l.missing.length > 0);

  return (
    <article className="border-t border-border pt-10 fade-up">
      <header className="mb-10 flex items-baseline justify-between gap-4">
        <h2 className="font-display text-3xl tracking-tight">
          Na mala · {capsule.total} {capsule.total === 1 ? "peça" : "peças"}
        </h2>
        {capsule.season && (
          <span className="tracking-label text-[11px] uppercase text-muted-foreground">
            {capsule.season}
          </span>
        )}
      </header>

      <div className="space-y-10">
        {capsule.groups.map((grp) => (
          <section key={grp.category}>
            <h3 className="tracking-label mb-4 text-[11px] uppercase text-muted-foreground">
              {CATEGORY_LABELS[grp.category] ?? titleCase(grp.category)} ·{" "}
              {grp.pieces.length}
            </h3>
            <div className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
              {grp.pieces.map((p, i) => (
                <figure
                  key={p.id}
                  className="fade-up"
                  style={{ animationDelay: `${i * 70}ms` }}
                >
                  <Link href={`/peca/${p.id}`} className="group block">
                    <div className="relative aspect-[3/4] overflow-hidden bg-muted">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/img/${p.id}`}
                        alt={p.description ?? p.category}
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
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
                  </Link>
                </figure>
              ))}
            </div>
          </section>
        ))}
      </div>

      <section className="mt-16">
        <h2 className="font-display mb-8 text-3xl tracking-tight">
          Um look por dia
        </h2>
        <div className="divide-y divide-border border-t border-border">
          {capsule.looks.map((l) => (
            <DayLook key={l.label} look={l} />
          ))}
        </div>
      </section>

      {uncovered.length > 0 && (
        <p className="mt-10 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
          ⚠️ O acervo não cobriu tudo:{" "}
          {uncovered
            .map(
              (l) =>
                `${l.label} ficou sem ${l.missing
                  .map((m) => MISSING_LABEL[m] ?? m)
                  .join(" e ")}`,
            )
            .join("; ")}
          . Cadastre essas peças pelo bot.
        </p>
      )}
    </article>
  );
}

function DayLook({ look }: { look: CapsuleLook }) {
  return (
    <div className="flex flex-wrap items-center gap-4 py-5">
      <div className="w-36 shrink-0">
        <p className="font-display text-lg leading-tight">{look.label}</p>
        {look.occasion && (
          <p className="tracking-label mt-1 text-[10px] uppercase text-muted-foreground">
            {look.occasion.replace(/_/g, " ")}
          </p>
        )}
      </div>
      <div className="flex flex-1 flex-wrap gap-2.5">
        {look.pieces.map((p) => (
          <Link
            key={p.id}
            href={`/peca/${p.id}`}
            title={p.description ?? p.category}
            className="block h-24 w-[4.5rem] overflow-hidden bg-muted transition-opacity hover:opacity-80"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/img/${p.id}`}
              alt={p.description ?? p.category}
              className="h-full w-full object-cover"
            />
          </Link>
        ))}
        {look.pieces.length === 0 && (
          <span className="text-sm italic text-muted-foreground">
            sem peças pra esse dia
          </span>
        )}
      </div>
    </div>
  );
}
