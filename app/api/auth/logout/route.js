import { NextResponse } from "next/server";

export async function POST() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  try {
    await fetch(`${apiBaseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Best-effort backend logout; cookie clear below is authoritative for app session.
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set({
    name: "access_token",
    value: "",
    path: "/",
    maxAge: 0,
  });
  return response;
}
