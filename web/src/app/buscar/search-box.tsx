"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Input } from "@/components/ui/input";

const SUGGESTIONS = [
  "blusa listrada",
  "algo pra inverno",
  "peça vinho",
  "look de viagem",
  "meia quentinha",
];

export function SearchBox({ initial }: { initial: string }) {
  const router = useRouter();
  const [q, setQ] = useState(initial);
  const [pending, startTransition] = useTransition();

  function submit(query: string) {
    const v = query.trim();
    if (!v) return;
    startTransition(() => router.push(`/buscar?q=${encodeURIComponent(v)}`));
  }

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(q);
        }}
        className="flex gap-2"
      >
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="descreva a peça… ex: blusa leve pra viagem"
          autoFocus
          className="h-11"
        />
        <button
          type="submit"
          disabled={pending}
          className="tracking-label shrink-0 rounded-md bg-primary px-5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Buscando…" : "Buscar"}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => {
              setQ(s);
              submit(s);
            }}
            className="tracking-label cursor-pointer rounded-full border border-border px-3 py-1.5 text-[11px] uppercase text-muted-foreground transition-colors hover:border-foreground hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
