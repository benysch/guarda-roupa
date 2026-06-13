import Link from "next/link";
import { logoutAction } from "@/app/actions";
import { countUnclassified } from "@/lib/wardrobe";

const NAV = [
  { href: "/", label: "Acervo" },
  { href: "/looks", label: "Looks" },
  { href: "/mala", label: "Mala" },
  { href: "/buscar", label: "Buscar" },
];

export async function SiteHeader({ active }: { active: string }) {
  let pending = 0;
  try {
    pending = await countUnclassified();
  } catch {
    pending = 0;
  }

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-display text-xl tracking-tight">
          O Guarda-Roupa
        </Link>
        <nav className="flex items-center gap-5 sm:gap-7">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`tracking-label text-[11px] uppercase transition-colors ${
                active === n.href
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {n.label}
            </Link>
          ))}
          {pending > 0 && (
            <Link
              href="/classificar"
              className={`tracking-label inline-flex items-center gap-1.5 text-[11px] uppercase transition-colors ${
                active === "/classificar"
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Classificar
              <span className="inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-primary px-1.5 py-0.5 text-[10px] leading-none text-primary-foreground">
                {pending}
              </span>
            </Link>
          )}
          <form action={logoutAction}>
            <button
              type="submit"
              className="tracking-label cursor-pointer text-[11px] uppercase text-muted-foreground transition-colors hover:text-foreground"
            >
              Sair
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
