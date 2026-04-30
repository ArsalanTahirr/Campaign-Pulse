import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LoginForm from "@/components/auth/LoginForm";

export default async function LoginPage({ searchParams }) {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const params = await searchParams;
  const inviteToken = params?.invite_token;
  const redirectPath = inviteToken ? `/invitations/accept/${encodeURIComponent(inviteToken)}` : "/dashboard";

  if (accessToken) {
    try {
      const meResponse = await fetch(`${apiBaseUrl}/auth/me`, {
        headers: { cookie: `access_token=${accessToken}` },
        cache: "no-store",
      });
      if (meResponse.ok) {
        redirect(redirectPath);
      }
    } catch {
      // If backend is unavailable, fall through and render login form.
    }
  }
  return <LoginForm inviteToken={inviteToken} />;
}
