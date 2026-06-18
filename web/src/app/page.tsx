import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { GarmentCard } from "@/components/garment-card";
import { listGarments, categoryCounts } from "@/lib/wardrobe";
import { CATEGORY_LABELS, CATEGORY_ORDER } from "@/lib/labels";

export const dynamic = "force-dynamic";

export default async function Home(props: {
  searchParams: Promise<{ cat?: string }>;
}) {
  const { cat } = await props.searchParams;
  const active = cat ?? "todos";
  const [garments, counts] = await Promise.all([
    listGarments(active),
    categoryCounts(),
  ]);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const cats = CATEGORY_ORDER.filter((c) => counts[c]);

  return (
    <>
      <SiteHeader active="/" />
      <main className="mx-auto max-w-6xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            {total} {total === 1 ? "peça" : "peças"} · estilo livre
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            O Acervo
          </h1>
        </section>

        <nav className="-mx-1 mb-10 flex flex-wrap gap-1.5">
          <Chip href="/" label={`Todos · ${total}`} active={active === "todos"} />
          {cats.map((c) => (
            <Chip
              key={c}
              href={`/?cat=${c}`}
              label={`${CATEGORY_LABELS[c]} · ${counts[c]}`}
              active={active === c}
            />
          ))}
        </nav>

        {garments.length === 0 ? (
          <p className="py-24 text-center text-muted-foreground">
            Nenhuma peça aqui ainda. Cadastre pelo bot do Telegram. 📸
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-x-5 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
            {garments.map((g, i) => (
              <GarmentCard key={g.id} g={g} index={i} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}

function Chip({
  href,
  label,
  active,
}: {
  href: string;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={`tracking-label rounded-full border px-3.5 py-1.5 text-[11px] uppercase transition-colors ${
        active
          ? "border-foreground bg-foreground text-background"
          : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}
