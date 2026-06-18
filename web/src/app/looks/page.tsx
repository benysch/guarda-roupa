import { SiteHeader } from "@/components/site-header";
import { composeLook, type LookResult } from "@/lib/brain";
import { titleCase } from "@/lib/labels";
import { LookControls } from "./look-controls";
import { LookImageButton } from "./look-image-button";
import { LookFeedback } from "./look-feedback";

export const dynamic = "force-dynamic";
// o estilista (Gemini) pode levar ~10-25s; dá folga à função
export const maxDuration = 60;

const MISSING_LABEL: Record<string, string> = {
  top: "um top",
  bottom: "uma calça ou saia",
  footwear: "um calçado",
  full_body: "um vestido/macacão",
};

const TEMP_LABEL: Record<string, string> = {
  frio: "❄️ Frio",
  ameno: "🌤️ Ameno",
  quente: "☀️ Quente",
};

const BOLD_LABEL: Record<string, string> = {
  discreto: "Discreto",
  equilibrado: "Equilibrado",
  ousado: "Ousado",
};

const OCC_LABEL: Record<string, string> = {
  dia_a_dia: "dia a dia",
  almoco_amigas: "almoço com amigas",
  jantar: "jantar",
  aniversario_infantil: "aniversário infantil",
};

export default async function LooksPage(props: {
  searchParams: Promise<{
    occasion?: string;
    season?: string;
    temp?: string;
    bold?: string;
    r?: string;
  }>;
}) {
  const sp = await props.searchParams;
  const requested = Boolean(
    sp.occasion || sp.season || sp.temp || sp.bold || sp.r,
  );
  const look = requested
    ? await composeLook(sp.occasion, sp.season, sp.temp, sp.bold)
    : null;

  return (
    <>
      <SiteHeader active="/looks" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Estilista · estilo livre
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Montar Look
          </h1>
        </section>

        <LookControls
          occasion={sp.occasion ?? ""}
          season={sp.season ?? ""}
          temperature={sp.temp ?? ""}
          boldness={sp.bold ?? ""}
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
    ? `Look ${OCC_LABEL[look.occasion] ?? look.occasion.replace(/_/g, " ")}`
    : "Seu look";

  return (
    <article className="border-t border-border pt-10 fade-up">
      <header className="mb-8 flex items-baseline justify-between gap-4">
        <h2 className="font-display text-3xl tracking-tight capitalize">
          {title}
        </h2>
        <span className="tracking-label flex shrink-0 gap-3 text-[11px] uppercase text-muted-foreground">
          {look.boldness && <span>{BOLD_LABEL[look.boldness] ?? look.boldness}</span>}
          {look.temperature && <span>{TEMP_LABEL[look.temperature] ?? look.temperature}</span>}
          {look.season && <span>{look.season}</span>}
        </span>
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
                {[titleCase(p.shade ?? p.primary_color), p.brand]
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

      {look.cold_without_coat && (
        <p className="mt-4 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
          🧥 Está frio e não há um casaco elegível no acervo — vale cadastrar um
          agasalho.
        </p>
      )}

      {look.model_image && look.look_id ? (
        <figure className="mt-10 border-t border-border pt-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/look-img/${look.look_id}`}
            alt="O look em uma modelo"
            className="w-full max-w-md rounded-md border border-border fade-up"
          />
          <figcaption className="tracking-label mt-3 text-[10px] uppercase text-muted-foreground">
            O look na modelo
          </figcaption>
        </figure>
      ) : (
        <LookImageButton
          ids={look.pieces.map((p) => p.id)}
          occasion={look.occasion ?? undefined}
          season={look.season ?? undefined}
        />
      )}

      <LookFeedback look={look} />
    </article>
  );
}
