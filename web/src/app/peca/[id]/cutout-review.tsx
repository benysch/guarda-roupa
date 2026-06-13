"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { decideCutout } from "./actions";

// Mostrado só quando cutout_status === 'pending': a foto original e o recorte
// proposto lado a lado, para você aprovar (passa a ser exibido no acervo) ou
// manter a original (descarta o recorte).
export function CutoutReview({ id }: { id: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();

  function decide(decision: "approved" | "rejected") {
    start(async () => {
      try {
        await decideCutout(id, decision);
        toast.success(
          decision === "approved" ? "Recorte aplicado" : "Mantida a original",
        );
        router.refresh();
      } catch {
        toast.error("Não consegui salvar a escolha");
      }
    });
  }

  return (
    <section className="mt-16 border-t border-border pt-10">
      <p className="tracking-label mb-1 text-[11px] uppercase text-muted-foreground">
        Recorte de fundo · revisão
      </p>
      <p className="mb-6 max-w-prose text-sm text-muted-foreground">
        Gerei uma versão sem fundo desta peça. Compare e escolha: se ficou bom,
        aplico no acervo; senão, mantenho a foto original.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <figure>
          <div className="relative aspect-[3/4] overflow-hidden bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/img/${id}`}
              alt="Foto original"
              className="h-full w-full object-cover"
            />
          </div>
          <figcaption className="tracking-label mt-2 text-[10px] uppercase text-muted-foreground">
            Original
          </figcaption>
        </figure>
        <figure>
          <div className="relative aspect-[3/4] overflow-hidden bg-[#f5f3f0] ring-1 ring-border">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/img/${id}?v=cutout`}
              alt="Recorte proposto"
              className="h-full w-full object-contain"
            />
          </div>
          <figcaption className="tracking-label mt-2 text-[10px] uppercase text-muted-foreground">
            Sem fundo (proposto)
          </figcaption>
        </figure>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => decide("approved")}
          disabled={pending}
          className="tracking-label rounded-md bg-primary px-6 py-2.5 text-[11px] uppercase text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Salvando…" : "Aplicar recorte"}
        </button>
        <button
          type="button"
          onClick={() => decide("rejected")}
          disabled={pending}
          className="tracking-label rounded-md px-4 py-2.5 text-[11px] uppercase text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          Manter original
        </button>
      </div>
    </section>
  );
}
