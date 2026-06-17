"use client";

import { useRef, useState } from "react";

type State = "idle" | "loading" | "done" | "error" | "quota";

export function LookImageButton({
  ids,
  occasion,
  season,
}: {
  ids: string[];
  occasion?: string;
  season?: string;
}) {
  const [state, setState] = useState<State>("idle");
  const [src, setSrc] = useState<string | null>(null);
  const inFlight = useRef(false);

  async function generate() {
    // Trava de re-entrância: ignora cliques enquanto uma geração está em curso.
    // Cobre rajadas de cliques no mesmo tick, antes do re-render desabilitar o botão.
    if (inFlight.current) return;
    inFlight.current = true;

    setState("loading");
    setSrc((prev) => {
      if (prev) URL.revokeObjectURL(prev); // libera o blob anterior ao regerar
      return null;
    });
    try {
      const p = new URLSearchParams({ ids: ids.join(",") });
      if (occasion) p.set("occasion", occasion);
      if (season) p.set("season", season);
      const res = await fetch(`/api/look-image?${p.toString()}`);
      const ct = res.headers.get("content-type") ?? "";
      if (res.ok && ct.startsWith("image/")) {
        const blob = await res.blob();
        setSrc(URL.createObjectURL(blob));
        setState("done");
      } else {
        const j = (await res.json().catch(() => ({}))) as { error?: string };
        setState(j.error === "quota" ? "quota" : "error");
      }
    } catch {
      setState("error");
    } finally {
      inFlight.current = false;
    }
  }

  const loading = state === "loading";

  return (
    <div className="mt-10 border-t border-border pt-8">
      {src ? (
        <figure>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt="O look em uma modelo (gerado por IA)"
            className="w-full max-w-md rounded-md border border-border fade-up"
          />
          <figcaption className="tracking-label mt-3 text-[10px] uppercase text-muted-foreground">
            Gerado por IA · interpretação aproximada das peças
          </figcaption>
          <button
            type="button"
            onClick={generate}
            disabled={loading}
            className="tracking-label mt-3 text-[11px] uppercase text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:opacity-50 disabled:no-underline disabled:hover:text-muted-foreground"
          >
            {loading ? "gerando…" : "↻ gerar de novo"}
          </button>
        </figure>
      ) : (
        <button
          type="button"
          onClick={generate}
          disabled={loading}
          className="tracking-label rounded-full border border-foreground px-6 py-2.5 text-[11px] uppercase transition-colors hover:bg-foreground hover:text-background disabled:opacity-50"
        >
          {loading ? "Gerando a modelo…" : "✨ Ver numa modelo"}
        </button>
      )}

      {state === "quota" && (
        <p className="mt-3 text-sm text-muted-foreground">
          A geração de imagem está indisponível agora (a chave do Gemini precisa
          de billing ativo). O resto do look funciona normalmente.
        </p>
      )}
      {state === "error" && (
        <p className="mt-3 text-sm text-destructive">
          Não consegui gerar a imagem agora. Tenta de novo em instantes.
        </p>
      )}
    </div>
  );
}
