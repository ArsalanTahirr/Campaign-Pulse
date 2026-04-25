import { redirect } from "next/navigation";

export default function DashboardIndexPage() {
  redirect("/dashboard/email-accounts");
}
