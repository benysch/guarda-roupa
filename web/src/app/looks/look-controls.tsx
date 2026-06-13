"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { toast } from "sonner";

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

const TEMPERATURES: [string, string][] = [
  ["", "Qualquer"],
  ["frio", "❄️ Frio"],
  ["ameno", "🌤️ Ameno"],
  ["quente", "☀️ Quente"],
];

/** °C -> faixa. Mesmo limiar do motor (looks.temp_from_celsius). */
function bandFromCelsius(c: number): string {
  if (c < 15) return "frio";
  if (c < 24) return "ameno";
  return "quente";
}

export function LookControls({
  occasion,
  season,
  temperature,
  hasLook,
}: {
  occasion: string;
  season: string;
  temperature: string;
  hasLook: boolean;
}) {
  const router = useRouter();
  const [occ, setOcc] = useState(occasion);
  const [sea, setSea] = useState(season);
  const [temp, setTemp] = useState(temperature);
  const [pending, startTransition] = useTransition();
  const [locating, setLocating] = useState(false);

  function go(nextOcc: string, nextSea: string, nextTemp: string) {
    const p = new URLSearchParams();
    if (nextOcc) p.set("occasion", nextOcc);
    if (nextSea) p.set("season", nextSea);
    if (nextTemp) p.set("temp", nextTemp);
    p.set("r", Math.random().toString(36).slice(2, 8));
    startTransition(() => router.push(`/looks?${p.toString()}`));
  }

  function useWeather() {
    if (!("geolocation" in navigator)) {
      toast.error("Seu navegador não tem geolocalização.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const res = await fetch(
            `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m`,
          );
          const data = await res.json();
          const c = data?.current?.temperature_2m;
          if (typeof c !== "number") throw new Error("sem dado");
          const band = bandFromCelsius(c);
          setTemp(band);
          toast.success(`Clima daqui: ${Math.round(c)}°C → ${band}`);
          go(occ, sea, band);
        } catch {
          toast.error("Não consegui pegar o clima agora.");
        } finally {
          setLocating(false);
        }
      },
      () => {
        setLocating(false);
        toast.error("Permissão de localização negada.");
      },
      { timeout: 10000 },
    );
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
              go(v, sea, temp);
            }}
          />
        ))}
      </Row>
      <Row label="Clima">
        {TEMPERATURES.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={temp === v}
            onClick={() => {
              setTemp(v);
              go(occ, sea, v);
            }}
          />
        ))}
        <button
          type="button"
          onClick={useWeather}
          disabled={locating}
          className="tracking-label cursor-pointer rounded-full border border-dashed border-border px-3 py-1.5 text-[11px] uppercase text-muted-foreground transition-colors hover:border-foreground hover:text-foreground disabled:opacity-50"
        >
          {locating ? "Localizando…" : "📍 Usar clima daqui"}
        </button>
      </Row>
      <Row label="Estação">
        {SEASONS.map(([v, l]) => (
          <Chip
            key={v}
            label={l}
            active={sea === v}
            onClick={() => {
              setSea(v);
              go(occ, v, temp);
            }}
          />
        ))}
      </Row>
      <button
        type="button"
        onClick={() => go(occ, sea, temp)}
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
