import { SiteHeader } from "@/components/site-header";

export default function LooksLoading() {
  return (
    <>
      <SiteHeader active="/looks" />
      <main className="mx-auto max-w-5xl px-6 pb-24">
        <section className="py-10 sm:py-14">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Estilista · estilo livre
          </p>
          <h1 className="font-display mt-3 text-5xl tracking-tight sm:text-6xl">
            Montar Look
          </h1>
        </section>
        <div className="border-t border-border py-24 text-center">
          <p className="font-display animate-pulse text-2xl italic text-muted-foreground">
            A estilista está montando seu look…
          </p>
        </div>
      </main>
    </>
  );
}
