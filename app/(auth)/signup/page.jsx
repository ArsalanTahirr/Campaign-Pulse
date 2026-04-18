import AuthShell from "@/components/auth/AuthShell";

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your account"
      subtitle="Start your free trial and scale cold outreach with confidence."
      submitLabel="Create Account"
      footerText="Already have an account?"
      footerAction="Sign in"
      footerHref="/login"
    />
  );
}
