import Link from "next/link";
import { COLOR_HEX, titleCase } from "@/lib/labels";
import type { Garment } from "@/lib/wardrobe";

export function GarmentCard({ g, index }: { g: Garment; index: number }) {
  return (
    <Link
      href={`/peca/${g.id}`}
      className="group block fade-up"
      style={{ animationDelay: `${Math.min(index, 14) * 40}ms` }}
    >
      <div className="relative aspect-[3/4] overflow-hidden bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/img/${g.id}`}
          alt={g.description ?? g.category}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
        />
        <span className="tracking-label absolute right-2 top-2 rounded-full bg-background/80 px-2.5 py-1 text-[10px] uppercase text-foreground opacity-80 backdrop-blur-sm transition-opacity group-hover:opacity-100">
          ✎ Editar
        </span>
      </div>
      <div className="mt-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-display truncate text-base leading-tight">
            {titleCase(g.subcategory ?? g.category)}
          </h3>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {[titleCase(g.primary_color), g.brand].filter(Boolean).join(" · ") ||
              "—"}
          </p>
        </div>
        {g.primary_color && (
          <span
            className="mt-1 h-3 w-3 shrink-0 rounded-full ring-1 ring-border"
            style={{ backgroundColor: COLOR_HEX[g.primary_color] ?? "#ccc" }}
            title={titleCase(g.primary_color)}
          />
        )}
      </div>
    </Link>
  );
}
