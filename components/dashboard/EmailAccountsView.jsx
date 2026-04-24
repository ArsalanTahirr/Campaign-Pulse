import Image from "next/image";
import { Hand, Link2 } from "lucide-react";

export default function EmailAccountsView({ hasContent = false, children = null }) {
  if (hasContent) {
    return (
      <section className="flex flex-1 px-6 py-10 sm:px-10">
        <div className="w-full">{children}</div>
      </section>
    );
  }

  return (
    <section className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
      <div className="flex w-full max-w-xl flex-col items-center gap-4 rounded-2xl bg-white/50 px-8 py-10 text-center backdrop-blur-sm">
        <Image
          src="/emailDood.png"
          alt="Email empty state doodle"
          width={800}
          height={800}
          className="h-auto w-full max-w-[460px] mix-blend-multiply"
          priority
        />

        <div className="mt-1 flex items-start justify-center gap-3 text-amber-500">
          <Hand
            fill="currentColor"
            className="mt-0.5 h-6 w-6 shrink-0 text-amber-500 stroke-amber-600 stroke-[1.4]"
          />
          <p className="text-lg font-semibold leading-tight text-slate-900 sm:text-xl">
            Add an email account to get started
          </p>
        </div>

        <button
          type="button"
          className="group mt-1 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-base font-semibold text-blue-600 transition-all duration-300 hover:bg-blue-50 hover:text-blue-700"
        >
          <Link2 className="h-4 w-4 transition-transform duration-300 group-hover:scale-110" />
          Add New
        </button>
      </div>
    </section>
  );
}
