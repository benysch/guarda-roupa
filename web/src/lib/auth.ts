import "server-only";
import { cookies } from "next/headers";
import { AUTH_COOKIE } from "./constants";

const THIRTY_DAYS = 60 * 60 * 24 * 30;

/** Valor opaco do cookie quando autenticado (segredo do servidor). */
function secret(): string {
  return process.env.AUTH_SECRET ?? "";
}

export async function isAuthed(): Promise<boolean> {
  const c = await cookies();
  return !!secret() && c.get(AUTH_COOKIE)?.value === secret();
}

export async function signIn(password: string): Promise<boolean> {
  const expected = process.env.APP_PASSWORD ?? "";
  if (expected && password === expected) {
    const c = await cookies();
    c.set(AUTH_COOKIE, secret(), {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: THIRTY_DAYS,
    });
    return true;
  }
  return false;
}

export async function signOut(): Promise<void> {
  const c = await cookies();
  c.delete(AUTH_COOKIE);
}
