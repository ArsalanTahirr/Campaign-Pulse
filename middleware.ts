import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/dashboard"];
const LOGIN_PATHS = new Set(["/login", "/auth/login"]);
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function hasValidSession(request: NextRequest, token: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { cookie: `access_token=${token}` },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  const token = request.cookies.get("access_token")?.value;
  const isAuthenticated = token ? await hasValidSession(request, token) : false;

  if (LOGIN_PATHS.has(pathname) && isAuthenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  if (LOGIN_PATHS.has(pathname) && token && !isAuthenticated) {
    const response = NextResponse.next();
    response.cookies.delete("access_token");
    return response;
  }

  if (!isProtected) return NextResponse.next();

  if (isAuthenticated) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  const response = NextResponse.redirect(loginUrl);
  if (token) {
    response.cookies.delete("access_token");
  }
  return response;
}

export const config = {
  // /invitations/accept/[token] is intentionally public — authentication
  // is handled inside the page component itself (redirects to login if needed).
  matcher: ["/dashboard/:path*", "/login", "/auth/login"],
};
