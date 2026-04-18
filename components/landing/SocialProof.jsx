import { SOCIAL_PROOF_STATS } from "@/lib/constants/landing";

export default function SocialProof() {
  return (
    <section className="section-shell pb-16">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-center text-sm font-semibold uppercase tracking-wide text-slate-500">
          Trusted by modern growth teams
        </p>
        <div className="mt-8 grid gap-6 text-center sm:grid-cols-3">
          {SOCIAL_PROOF_STATS.map((item) => (
            <div key={item.label}>
              <p className="text-3xl font-bold text-slate-900">{item.value}</p>
              <p className="mt-2 text-sm text-slate-600">{item.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
