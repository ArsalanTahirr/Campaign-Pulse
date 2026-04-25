import { redirect } from "next/navigation";

export default function DashboardIndexPage({ searchParams }) {
  const params = new URLSearchParams();
  if (searchParams?.login_type) params.set("login_type", searchParams.login_type);
  if (searchParams?.welcome_name) params.set("welcome_name", searchParams.welcome_name);
  const queryString = params.toString();
  redirect(`/dashboard/email-accounts${queryString ? `?${queryString}` : ""}`);
}
