"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import type { LookResult } from "@/lib/brain";
import { rateLook, type Verdict } from "./feedback";

/** 👍 / 👎 numa composição — alimenta a curadoria do estilista. */
export function LookFeedback({ look }: { look: LookResult }) {
  const [done, setDone] = useState<Verdict | null>(null);
  const [pending, startTransition] = useTransition();

  function rate(verdict: Verdict) {
    if (done || pending) return;
    startTransition(async () => {
      const res = await rateLook(
        {
          look_id: look.look_id,
          occasion: look.occasion,
          season: look.season,
          temperature: look.temperature,
          boldness: look.boldness,
          rationale: look.rationale,
          pieces: look.pieces,
        },
        verdict,
      );
      if (!res.ok) {
        toast.error("Não consegui registrar agora. Tenta de novo?");
        return;
      }
      setDone(verdict);
      toast.success(
        verdict === "gostei"
          ? "Anotado! Vou trazer mais nesse estilo. 💛"
          : "Valeu — esse não volta. Vou ajustar o gosto.",
      );
    });
  }

  if (done) {
    return (
      <p className="tracking-label mt-10 text-[11px] uppercase text-muted-foreground">
        {done === "gostei" ? "💛 Você curtiu este look" : "👎 Anotado — vou afinar"}
      </p>
    );
  }

  return (
    <div className="mt-10 flex items-center gap-3">
      <span className="tracking-label text-[10px] uppercase text-muted-foreground">
        O que achou?
      </span>
      <button
        type="button"
        onClick={() => rate("gostei")}
        disabled={pending}
        className="cursor-pointer rounded-full border border-border px-4 py-1.5 text-sm transition-colors hover:border-foreground disabled:opacity-50"
      >
        👍 Gostei
      </button>
      <button
        type="button"
        onClick={() => rate("nao_gostei")}
        disabled={pending}
        className="cursor-pointer rounded-full border border-border px-4 py-1.5 text-sm transition-colors hover:border-foreground disabled:opacity-50"
      >
        👎 Não gostei
      </button>
    </div>
  );
}
