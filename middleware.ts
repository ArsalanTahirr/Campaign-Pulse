import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/dashboard"];
const LOGIN_PATHS = new Set(["/login", "/auth/login"]);

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  const token = request.cookies.get("access_token")?.value;

  if (LOGIN_PATHS.has(pathname) && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (!isProtected) return NextResponse.next();

  if (token) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/auth/login"],
};
