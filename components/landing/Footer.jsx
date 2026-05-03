// Footer updated: link architecture, academic branding,
// hover effects — Team Infinity, NUCES-Khi
// Backend: no changes made

import Image from "next/image";
import Link from "next/link";
import { Github, Linkedin, Twitter } from "lucide-react";

const FooterLink = ({ href, children, external = false }) => {
  const cls =
    "text-sm text-slate-400 hover:text-indigo-400 hover:translate-x-1 " +
    "transition-all duration-200 ease-out inline-block w-fit";
  return external ? (
    <a href={href} className={cls}
       target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ) : (
    <Link href={href} className={cls}>{children}</Link>
  );
};

const SocialIcon = ({ href, label, children }) => (
  <a href={href} aria-label={label}
     target="_blank" rel="noopener noreferrer"
     className="text-slate-400 hover:text-white hover:scale-110
       transition-all duration-200 ease-out p-2 rounded-lg
       hover:bg-white/5">
    {children}
  </a>
);

export default function Footer() {
  return (
    <footer className="bg-[#020617] text-slate-300">
      <div className="max-w-7xl mx-auto px-6 py-16 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4 lg:gap-12">
          {/* Brand Column */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="inline-flex items-center gap-3">
              <Image src="/icon.png" alt="CampaignPulse logo" width={34} height={34} />
              <span className="text-xl font-semibold tracking-tight text-white">CampaignPulse</span>
            </Link>
            <p className="mt-5 max-w-xs text-sm leading-relaxed text-slate-400">
              Empowering your email outreach with precision analytics and real-time pulse tracking.
            </p>
            <div className="flex gap-3 mt-5">
              <SocialIcon href="https://github.com" label="GitHub">
                <Github className="h-5 w-5" strokeWidth={1.8} />
              </SocialIcon>
              <SocialIcon href="https://linkedin.com" label="LinkedIn">
                <Linkedin className="h-5 w-5" strokeWidth={1.8} />
              </SocialIcon>
              <SocialIcon href="https://twitter.com" label="Twitter">
                <Twitter className="h-5 w-5" strokeWidth={1.8} />
              </SocialIcon>
            </div>
          </div>

          {/* Product Column */}
          <div className="col-span-1">
            <h3 className="text-xs font-semibold tracking-widest uppercase text-slate-300 mb-4">
              Product
            </h3>
            <div className="flex flex-col gap-3">
              <FooterLink href="/features">Features</FooterLink>
              <FooterLink href="/pricing">Pricing</FooterLink>
              <FooterLink href="/features#ai-warmup">AI Warmup</FooterLink>
              <FooterLink href="/features#analytics">Analytics</FooterLink>
              <FooterLink href="/customers">Customers</FooterLink>
            </div>
          </div>

          {/* Resources Column */}
          <div className="col-span-1">
            <h3 className="text-xs font-semibold tracking-widest uppercase text-slate-300 mb-4">
              Resources
            </h3>
            <div className="flex flex-col gap-3">
              <FooterLink href="/resources">Knowledge Base</FooterLink>
              <FooterLink href="/docs" external>API Docs</FooterLink>
              <FooterLink href="/demo">Watch Demo</FooterLink>
            </div>
          </div>

          {/* Legal Column */}
          <div className="col-span-1">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4">
              Legal
            </h3>
            <div className="flex flex-col space-y-3">
              <Link href="/privacy" className="text-sm text-gray-400 hover:text-white transition-colors duration-150 inline-block w-fit">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm text-gray-400 hover:text-white transition-colors duration-150 inline-block w-fit">
                Terms
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-6 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500">© 2026 CampaignPulse. All rights reserved.</p>
          <div className="flex gap-4">
            <Link href="/privacy" className="text-xs text-slate-500 hover:text-indigo-400 transition-colors duration-150">
              Privacy
            </Link>
            <span className="text-xs text-slate-600">·</span>
            <Link href="/terms" className="text-xs text-slate-500 hover:text-indigo-400 transition-colors duration-150">
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
