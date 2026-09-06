import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const secretKey = () =>
  new TextEncoder().encode(process.env.SESSION_SECRET || "sis-dev-secret-change-me");

const PUBLIC = new Set(["/login", "/register"]);

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC.has(pathname)) return NextResponse.next();

  const tok = req.cookies.get("sis_session")?.value;
  if (tok) {
    try {
      await jwtVerify(tok, secretKey());
      return NextResponse.next();
    } catch {
      /* invalid / expired -> fall through to redirect */
    }
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  return NextResponse.redirect(url);
}

// Everything except Next internals and the public static folders.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|assets/|challenges/).*)"],
};
