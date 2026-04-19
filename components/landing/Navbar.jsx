import Image from "next/image";
import Link from "next/link";
import { NAV_LINKS } from "@/lib/constants/navigation";

const primaryCtaClassName =
  "inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition duration-200 bg-brand-600 text-white shadow-lg shadow-brand-500/30 hover:bg-brand-700";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
      <div className="section-shell flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/icon.png" alt="CampaignPulse logo" width={34} height={34} />
          <span className="text-lg font-bold tracking-tight">CampaignPulse</span>
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link}
              href="#"
              className="text-sm text-slate-600 transition hover:text-slate-900"
            >
              {link}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/login"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:border-pulseTeal hover:text-pulseTeal md:px-4"
          >
            Login
          </Link>
          <Link href="/signup" className={primaryCtaClassName}>
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}
