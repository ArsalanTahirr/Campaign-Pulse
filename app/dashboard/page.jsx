import { redirect } from "next/navigation";

export default async function DashboardIndexPage({ searchParams }) {
  const sp = await searchParams;
  const params = new URLSearchParams();
  if (sp?.login_type) params.set("login_type", sp.login_type);
  if (sp?.welcome_name) params.set("welcome_name", sp.welcome_name);
  const queryString = params.toString();
  redirect(`/dashboard/email-accounts${queryString ? `?${queryString}` : ""}`);
}
