import { SOCIAL_PROOF_STATS } from "@/lib/constants/landing";

export default function SocialProof() {
  return (
    <section className="section-shell pb-20 sm:pb-28">
      <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition-all duration-300 hover:shadow-md">
        {/* Subtle background flair */}
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-brand-50 blur-3xl opacity-50" />
        <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-sky-50 blur-3xl opacity-50" />
        
        <div className="relative p-10 sm:p-14">
          <p className="text-center text-sm font-bold uppercase tracking-widest text-brand-600">
            Trusted by modern growth teams
          </p>
          <div className="mt-10 grid gap-8 text-center sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
            {SOCIAL_PROOF_STATS.map((item) => (
              <div key={item.label} className="pt-8 sm:pt-0 first:pt-0 flex flex-col items-center justify-center">
                <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
                  {item.value}
                </p>
                <p className="mt-3 text-sm font-medium text-slate-500 uppercase tracking-wide">
                  {item.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
