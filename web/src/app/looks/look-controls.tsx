"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

const OCCASIONS: [string, string][] = [
  ["", "Qualquer"],
  ["dia", "Dia a dia"],
  ["trabalho", "Trabalho"],
  ["festa", "Festa"],
  ["encontro", "Encontro"],
  ["viagem", "Viagem"],
  ["praia", "Praia"],
  ["casa", "Casa"],
  ["casamento", "Casamento"],
];

const SEASONS: [string, string][] = [
  ["", "Qualquer estação"],
  ["verao", "Verão"],
  ["outono", "Outono"],
  ["inverno", "Inverno"],
  ["primavera", "Primavera"],
];

export function LookControls({
  occasion,
  season,
  hasLook,
}: {
  occasion: string;
  season: string;
  hasLook: boolean;
}) {
  const router = useRouter();
  const [occ, setOcc] = useState(occasion);
  const [sea, setSea] = useState(season);
  const [pending, startTransition] = useTransition();

  function go(nextOcc: string, nextSea: string) {
    const p = new URLSearchParams();
    if (nextOcc) p.set("occasion", nextOcc);
    if (nextSea) p.set("season", nextSea);
    p.set("r", Math.random().toString(36).slice(2, 8));
    startTransition(() => router.push(`/looks?${p.toString()}`));
  }

  return (
    <div className="space-y-5">
      <Row label="Ocasião">
        {OCCASIONS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={occ === v}
            onClick={() => {
              setOcc(v);
              go(v, sea);
            }}
          />
        ))}
      </Row>
      <Row label="Estação">
        {SEASONS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={sea === v}
            onClick={() => {
              setSea(v);
              go(occ, v);
            }}
          />
        ))}
      </Row>
      <button
        type="button"
        onClick={() => go(occ, sea)}
        disabled={pending}
        className="tracking-label mt-2 rounded-full bg-primary px-6 py-2.5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {pending ? "Montando…" : hasLook ? "↻ Montar outro" : "Montar look"}
      </button>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="tracking-label mr-2 w-16 shrink-0 text-[10px] uppercase text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`tracking-label cursor-pointer rounded-full border px-3 py-1.5 text-[11px] uppercase transition-colors ${
        active
          ? "border-foreground bg-foreground text-background"
          : "border-border text-muted-foreground hover:border-foreground hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );
}
