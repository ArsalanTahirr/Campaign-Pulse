import Image from "next/image";
import Link from "next/link";
import { Github, Linkedin, Twitter } from "lucide-react";
import {
  FOOTER_COMPANY_LINKS,
  FOOTER_LEGAL_LINKS,
  FOOTER_PRODUCT_LINKS
} from "@/lib/constants/footer";

export default function Footer() {
  return (
    <footer className="bg-slate-950 text-slate-200">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-16 sm:grid-cols-2 lg:grid-cols-4 lg:px-10">
        <div className="sm:col-span-2 lg:col-span-1">
          <Link href="/" className="inline-flex items-center gap-3">
            <Image src="/icon.png" alt="CampaignPulse logo" width={34} height={34} />
            <span className="text-xl font-semibold tracking-tight text-slate-100">CampaignPulse</span>
          </Link>
          <p className="mt-5 max-w-xs text-sm leading-relaxed text-slate-400">
            Empowering your email outreach with precision analytics and real-time pulse tracking.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-100">Product</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {FOOTER_PRODUCT_LINKS.map((link) => (
              <li key={link}>
                <Link href="#" className="text-slate-400 transition-colors duration-200 hover:text-sky-400">
                  {link}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-100">Company</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {FOOTER_COMPANY_LINKS.map((link) => (
              <li key={link}>
                <Link href="#" className="text-slate-400 transition-colors duration-200 hover:text-sky-400">
                  {link}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-100">Legal</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {FOOTER_LEGAL_LINKS.map((link) => (
              <li key={link}>
                <Link href="#" className="text-slate-400 transition-colors duration-200 hover:text-sky-400">
                  {link}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-slate-800">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 py-6 text-sm text-slate-400 sm:flex-row lg:px-10">
          <p>© 2026 CampaignPulse. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <Link href="#" aria-label="Twitter" className="transition-colors duration-200 hover:text-sky-400">
              <Twitter className="h-5 w-5" strokeWidth={1.8} />
            </Link>
            <Link href="#" aria-label="LinkedIn" className="transition-colors duration-200 hover:text-sky-400">
              <Linkedin className="h-5 w-5" strokeWidth={1.8} />
            </Link>
            <Link href="#" aria-label="GitHub" className="transition-colors duration-200 hover:text-slate-100">
              <Github className="h-5 w-5" strokeWidth={1.8} />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
