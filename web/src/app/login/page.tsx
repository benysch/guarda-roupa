import { redirect } from "next/navigation";
import { signIn } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default async function LoginPage(props: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await props.searchParams;

  async function action(formData: FormData) {
    "use server";
    const ok = await signIn(String(formData.get("password") ?? ""));
    redirect(ok ? "/" : "/login?error=1");
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-background px-6">
      <div className="w-full max-w-sm fade-up">
        <div className="mb-10 text-center">
          <p className="tracking-label text-[11px] uppercase text-muted-foreground">
            Inverno Frio · Edição
          </p>
          <h1 className="font-display mt-3 text-5xl leading-none tracking-tight">
            O Guarda-Roupa
          </h1>
          <p className="mt-4 text-sm text-muted-foreground">
            O acervo da Muri. Acesso restrito.
          </p>
        </div>

        <form action={action} className="space-y-3">
          <Input
            name="password"
            type="password"
            placeholder="Senha de família"
            autoFocus
            required
            className="h-11 text-center"
          />
          {error && (
            <p className="text-center text-sm text-destructive">
              Senha incorreta.
            </p>
          )}
          <Button type="submit" className="h-11 w-full">
            Entrar
          </Button>
        </form>
      </div>
    </main>
  );
}
