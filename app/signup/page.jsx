import { redirect } from "next/navigation";

export default function SignupPageAlias() {
  redirect("/auth/signup");
}
