import { SiteHeader } from "@/components/site-header";
import {
  packCapsule,
  type CapsuleResult,
  type LookPiece,
  type TripDay,
} from "@/lib/brain";
import { CATEGORY_LABELS, CATEGORY_ORDER, titleCase } from "@/lib/labels";
import { TripBuilder } from "./trip-builder";

export const dynamic = "force-dynamic";
// busca o acervo no Supabase + roda a engine; folga generosa.
export const maxDuration = 30;

const MISSING_LABEL: Record<string, string> = {
  top: "um top",
  bottom: "uma calça ou saia",
  footwear: "um calçado",
  full_body: "um vestido/macacão",
};

function parseTrip(raw: string | undefined): TripDay[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((d) => ({
        season: typeof d?.season === "string" ? d.season : "",
        occasions: Array.isArray(d?.occasions)
          ? d.occasions.filter((o: unknown): o is string => typeof o === "string")
          : [],
      }))
      .filter((d) => d.occasions.length > 0);
  } catch {
    return [];
  }
}

export default async function ViagemPage(props: {
  searchParams: Promise<{ trip?: string; bag?: string; r?: string }>;
}) {
  const sp = await props.searchParams;
  const trip = parseTrip(sp.trip);
  const includeBag = sp.bag !== "0";
  const capsule = trip.length ? await packCapsule(trip, includeBag) : null;

  return (
    <>
      <SiteHeader active="/viagem" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Mala de viagem · cápsula
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Fazer a Mala
          </h1>
          <p className="mt-4 max-w-xl text-sm text-muted-foreground">
            Monte a viagem dia a dia — o clima e os looks de cada dia. A engine
            encontra a <em>menor</em> mala que cobre todos os looks, rodando as
            blusas sobre poucas bases.
          </p>
        </section>

        <TripBuilder initialDays={trip} includeBag={includeBag} />

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
        Adicione os dias da viagem — a mala se monta sozinha.
      </p>
    </div>
  );
}

function CapsuleView({ capsule }: { capsule: CapsuleResult }) {
  if (capsule.count === 0) {
    return (
      <div className="border-t border-border py-24 text-center text-muted-foreground">
        Ainda não tenho peças suficientes pra montar a mala. Cadastre mais pelo
        bot. 📸
      </div>
    );
  }

  const groups = CATEGORY_ORDER.filter(
    (c) => (capsule.suitcase[c]?.length ?? 0) > 0,
  );

  return (
    <article className="border-t border-border pt-10 fade-up">
      {/* --- A mala (lista mínima por categoria) --- */}
      <header className="mb-8 flex items-baseline justify-between gap-4">
        <h2 className="font-display text-3xl tracking-tight">A mala</h2>
        <span className="tracking-label text-[11px] uppercase text-muted-foreground">
          {capsule.count} peça{capsule.count === 1 ? "" : "s"}
        </span>
      </header>

      <div className="space-y-10">
        {groups.map((cat) => (
          <div key={cat}>
            <p className="tracking-label mb-4 text-[11px] uppercase text-muted-foreground">
              {CATEGORY_LABELS[cat] ?? titleCase(cat)}
            </p>
            <div className="grid grid-cols-3 gap-x-5 gap-y-8 sm:grid-cols-4 lg:grid-cols-5">
              {capsule.suitcase[cat].map((p, i) => (
                <PieceFigure key={p.id} piece={p} delay={i * 60} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* --- Os looks de cada dia --- */}
      <h2 className="font-display mt-16 mb-8 text-3xl tracking-tight">
        Os looks
      </h2>
      <div className="space-y-12">
        {capsule.days.map((day) => (
          <section key={day.label}>
            <header className="mb-5 flex items-baseline gap-3">
              <h3 className="font-display text-2xl tracking-tight">
                {day.label}
              </h3>
              {day.season && (
                <span className="tracking-label text-[10px] uppercase text-muted-foreground">
                  {day.season}
                </span>
              )}
            </header>
            <div className="space-y-8">
              {day.looks.map((look) => (
                <div key={look.label}>
                  <p className="mb-3 text-sm capitalize text-muted-foreground">
                    {look.occasion?.replace(/_/g, " ") ?? "look"}
                  </p>
                  <div className="grid grid-cols-3 gap-x-5 gap-y-6 sm:grid-cols-4 lg:grid-cols-5">
                    {look.pieces.map((p, i) => (
                      <PieceFigure key={p.id} piece={p} delay={i * 50} />
                    ))}
                  </div>
                  {look.missing.length > 0 && (
                    <p className="mt-3 text-sm text-muted-foreground">
                      ⚠️ Faltou{" "}
                      {look.missing
                        .map((m) => MISSING_LABEL[m] ?? m)
                        .join(", ")}
                      .
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* --- Lacunas: insumo de gap analysis --- */}
      {capsule.uncovered.length > 0 && (
        <div className="mt-12 rounded-md bg-muted px-4 py-4 text-sm text-muted-foreground">
          <p className="mb-1 font-medium text-foreground">
            Lacunas da viagem
          </p>
          <ul className="list-disc space-y-1 pl-5">
            {capsule.uncovered.map((u) => (
              <li key={u.label}>
                <span className="capitalize">{u.label}</span>: falta{" "}
                {u.missing.map((m) => MISSING_LABEL[m] ?? m).join(", ")}.
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function PieceFigure({ piece, delay }: { piece: LookPiece; delay: number }) {
  return (
    <figure className="fade-up" style={{ animationDelay: `${delay}ms` }}>
      <div className="relative aspect-[3/4] overflow-hidden bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/img/${piece.id}`}
          alt={piece.description ?? piece.category}
          className="h-full w-full object-cover"
        />
      </div>
      <figcaption className="mt-2">
        <p className="font-display text-sm leading-tight">
          {titleCase(piece.subcategory ?? piece.category)}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {[titleCase(piece.primary_color), piece.brand]
            .filter(Boolean)
            .join(" · ") || "—"}
        </p>
      </figcaption>
    </figure>
  );
}
