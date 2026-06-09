import { SiteHeader } from "@/components/site-header";

export default function BuscarPage() {
  return (
    <>
      <SiteHeader active="/buscar" />
      <main className="mx-auto grid min-h-[60vh] max-w-6xl place-items-center px-6">
        <div className="text-center">
          <h1 className="font-display text-4xl tracking-tight">Buscar</h1>
          <p className="mt-3 text-sm text-muted-foreground">
            Busca por descrição (semântica). Em breve.
          </p>
        </div>
      </main>
    </>
  );
}
