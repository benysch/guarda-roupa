import { SiteHeader } from "@/components/site-header";

export default function MalaLoading() {
  return (
    <>
      <SiteHeader active="/mala" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Cápsula mínima · paleta inverno frio
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Mala de Viagem
          </h1>
        </section>
        <div className="border-t border-border py-24 text-center">
          <p className="font-display animate-pulse text-2xl italic text-muted-foreground">
            Empacotando a menor mala possível…
          </p>
        </div>
      </main>
    </>
  );
}
