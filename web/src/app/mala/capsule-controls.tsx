"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

const DAYS: [string, string][] = [
  ["2", "2 dias"],
  ["3", "3 dias"],
  ["4", "4 dias"],
  ["5", "5 dias"],
  ["7", "1 semana"],
];

const OCCASIONS: [string, string][] = [
  ["", "Qualquer"],
  ["dia", "Dia a dia"],
  ["viagem", "Passeio"],
  ["trabalho", "Trabalho"],
  ["praia", "Praia"],
];

const NIGHTS: [string, string][] = [
  ["", "Sem noite"],
  ["encontro", "Jantar"],
  ["festa", "Festa"],
];

const SEASONS: [string, string][] = [
  ["", "Qualquer estação"],
  ["verao", "Verão"],
  ["outono", "Outono"],
  ["inverno", "Inverno"],
  ["primavera", "Primavera"],
];

export function CapsuleControls({
  days,
  occasion,
  night,
  season,
  hasCapsule,
}: {
  days: string;
  occasion: string;
  night: string;
  season: string;
  hasCapsule: boolean;
}) {
  const router = useRouter();
  const [d, setD] = useState(days || "3");
  const [occ, setOcc] = useState(occasion);
  const [ngt, setNgt] = useState(night);
  const [sea, setSea] = useState(season);
  const [pending, startTransition] = useTransition();

  function go(next: { d?: string; occ?: string; ngt?: string; sea?: string }) {
    const p = new URLSearchParams();
    p.set("days", next.d ?? d);
    if (next.occ ?? occ) p.set("occasion", next.occ ?? occ);
    if (next.ngt ?? ngt) p.set("night", next.ngt ?? ngt);
    if (next.sea ?? sea) p.set("season", next.sea ?? sea);
    startTransition(() => router.push(`/mala?${p.toString()}`));
  }

  return (
    <div className="space-y-5">
      <Row label="Duração">
        {DAYS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={d === v}
            onClick={() => {
              setD(v);
              go({ d: v });
            }}
          />
        ))}
      </Row>
      <Row label="Dias">
        {OCCASIONS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={occ === v}
            onClick={() => {
              setOcc(v);
              go({ occ: v });
            }}
          />
        ))}
      </Row>
      <Row label="Noites">
        {NIGHTS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={ngt === v}
            onClick={() => {
              setNgt(v);
              go({ ngt: v });
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
              go({ sea: v });
            }}
          />
        ))}
      </Row>
      <button
        type="button"
        onClick={() => go({})}
        disabled={pending}
        className="tracking-label mt-2 rounded-full bg-primary px-6 py-2.5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {pending ? "Empacotando…" : hasCapsule ? "↻ Refazer a mala" : "Fazer a mala"}
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
