'use client';

import Image from "next/image";
import Link from "next/link";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";

const navLinks = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "Customers", href: "/customers" },
  { label: "Resources", href: "/resources" }
];

const primaryCtaClassName =
  "inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition duration-200 bg-indigo-600 text-white shadow-lg shadow-indigo-500/30 hover:bg-indigo-700";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <header 
      className={`sticky top-0 z-40 transition-all duration-300 ${
        scrolled 
          ? 'bg-white/70 backdrop-blur-xl border-b border-white/20 shadow-sm' 
          : 'bg-white/80 border-b border-transparent'
      }`}
    >
      <div className="max-w-full px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <Image src="/icon.png" alt="CampaignPulse logo" width={34} height={34} />
            <span className="text-lg font-bold tracking-tight text-gray-900">CampaignPulse</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <motion.div
                key={link.href}
                whileHover={{ backgroundColor: "rgba(224, 231, 255, 0.5)" }}
                transition={{ duration: 0.3 }}
                className="rounded-lg px-3 py-2"
              >
                <Link
                  href={link.href}
                  className="text-sm font-medium text-gray-600"
                >
                  <motion.span
                    initial={{ color: "rgb(75, 85, 99)" }}
                    whileHover={{ color: "rgb(79, 70, 229)" }}
                    transition={{ duration: 0.3 }}
                    className="block"
                  >
                    {link.label}
                  </motion.span>
                </Link>
              </motion.div>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm transition hover:border-gray-300 hover:text-gray-900"
            >
              Login
            </Link>
            <Link href="/signup" className={primaryCtaClassName}>
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden inline-flex items-center justify-center p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition"
            aria-label="Toggle menu"
          >
            <svg
              className={`w-6 h-6 transition-transform duration-300 ${mobileOpen ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Mobile CTAs */}
          <div className="md:hidden flex items-center gap-2">
            <Link href="/signup" className="rounded-lg px-3 py-2 text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition">
              Get Started
            </Link>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileOpen && (
          <nav className="md:hidden border-t border-gray-200 bg-white/95 backdrop-blur py-4 space-y-3">
            {navLinks.map((link) => (
              <motion.div
                key={link.href}
                whileHover={{ backgroundColor: "rgba(224, 231, 255, 0.5)" }}
                transition={{ duration: 0.3 }}
                className="rounded-lg"
              >
                <Link
                  href={link.href}
                  className="block px-4 py-2 text-sm font-medium text-gray-600 rounded-lg"
                  onClick={() => setMobileOpen(false)}
                >
                  <motion.span
                    initial={{ color: "rgb(75, 85, 99)" }}
                    whileHover={{ color: "rgb(79, 70, 229)" }}
                    transition={{ duration: 0.3 }}
                    className="block"
                  >
                    {link.label}
                  </motion.span>
                </Link>
              </motion.div>
            ))}
            <Link
              href="/login"
              className="block px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition"
              onClick={() => setMobileOpen(false)}
            >
              Login
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
