import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE } from "@/lib/constants";

// Next.js 16: "middleware" foi renomeado para "proxy" (runtime nodejs).
// Porta de acesso: tudo exige o cookie de sessão, exceto /login e estáticos.
export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const authed = req.cookies.get(AUTH_COOKIE)?.value === process.env.AUTH_SECRET;

  if (!authed && pathname !== "/login") {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  if (authed && pathname === "/login") {
    const url = req.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
