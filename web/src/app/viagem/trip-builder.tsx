"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import type { TripDay } from "@/lib/brain";

// Ocasiões válidas para um dia de viagem (espelham os valores do cérebro;
// "viagem" fica de fora — a viagem inteira já é o contexto).
const OCCASIONS: [string, string][] = [
  ["dia", "Dia a dia"],
  ["trabalho", "Trabalho"],
  ["festa", "Festa"],
  ["encontro", "Encontro"],
  ["praia", "Praia"],
  ["academia", "Academia"],
  ["casa", "Casa"],
  ["casamento", "Casamento"],
];

const SEASONS: [string, string][] = [
  ["", "Qualquer"],
  ["verao", "Verão"],
  ["outono", "Outono"],
  ["inverno", "Inverno"],
  ["primavera", "Primavera"],
];

function emptyDay(season = ""): TripDay {
  return { season, occasions: [] };
}

export function TripBuilder({
  initialDays,
  includeBag,
}: {
  initialDays: TripDay[];
  includeBag: boolean;
}) {
  const router = useRouter();
  const [days, setDays] = useState<TripDay[]>(
    initialDays.length ? initialDays : [emptyDay()],
  );
  const [bag, setBag] = useState(includeBag);
  const [pending, startTransition] = useTransition();

  function patchDay(i: number, patch: Partial<TripDay>) {
    setDays((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)));
  }

  function toggleOccasion(i: number, occ: string) {
    setDays((ds) =>
      ds.map((d, j) =>
        j === i
          ? {
              ...d,
              occasions: d.occasions.includes(occ)
                ? d.occasions.filter((o) => o !== occ)
                : [...d.occasions, occ],
            }
          : d,
      ),
    );
  }

  function addDay() {
    setDays((ds) => [...ds, emptyDay(ds[ds.length - 1]?.season ?? "")]);
  }

  function removeDay(i: number) {
    setDays((ds) => (ds.length > 1 ? ds.filter((_, j) => j !== i) : ds));
  }

  const totalLooks = days.reduce((n, d) => n + d.occasions.length, 0);

  function pack() {
    const trip = days.filter((d) => d.occasions.length > 0);
    if (!trip.length) return;
    const p = new URLSearchParams();
    p.set("trip", JSON.stringify(trip));
    if (!bag) p.set("bag", "0");
    p.set("r", Math.random().toString(36).slice(2, 8));
    startTransition(() => router.push(`/viagem?${p.toString()}`));
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {days.map((day, i) => (
          <div
            key={i}
            className="rounded-lg border border-border p-4 sm:p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <span className="font-display text-lg tracking-tight">
                Dia {i + 1}
              </span>
              {days.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeDay(i)}
                  className="tracking-label cursor-pointer text-[10px] uppercase text-muted-foreground transition-colors hover:text-foreground"
                >
                  Remover
                </button>
              )}
            </div>

            <Row label="Clima">
              {SEASONS.map(([v, l]) => (
                <Chip
                  key={v}
                  label={l}
                  active={day.season === v}
                  onClick={() => patchDay(i, { season: v })}
                />
              ))}
            </Row>
            <div className="mt-3">
              <Row label="Looks">
                {OCCASIONS.map(([v, l]) => (
                  <Chip
                    key={v}
                    label={l}
                    active={day.occasions.includes(v)}
                    onClick={() => toggleOccasion(i, v)}
                  />
                ))}
              </Row>
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={addDay}
        className="tracking-label cursor-pointer rounded-full border border-border px-4 py-2 text-[11px] uppercase text-muted-foreground transition-colors hover:border-foreground hover:text-foreground"
      >
        + Adicionar dia
      </button>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-border pt-5">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={bag}
            onChange={(e) => setBag(e.target.checked)}
            className="h-4 w-4 accent-foreground"
          />
          Levar uma bolsa
        </label>
        <button
          type="button"
          onClick={pack}
          disabled={pending || totalLooks === 0}
          className="tracking-label rounded-full bg-primary px-6 py-2.5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {pending
            ? "Montando…"
            : `Montar mala · ${totalLooks} look${totalLooks === 1 ? "" : "s"}`}
        </button>
      </div>
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
      <span className="tracking-label mr-2 w-12 shrink-0 text-[10px] uppercase text-muted-foreground">
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
