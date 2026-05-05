"use client";

import { usePathname } from "next/navigation";
import Navbar from "@/components/landing/Navbar";
import Footer from "@/components/landing/Footer";

/**
 * Routes that should NOT show the public Navbar/Footer.
 * The dashboard has its own Sidebar; auth pages are standalone.
 */
const PRIVATE_PREFIXES = [
  "/dashboard",
  "/login",
  "/signup",
  "/auth",
  "/invitations",
  "/reset-password",
  "/api",
];

function isPublicRoute(pathname) {
  return !PRIVATE_PREFIXES.some((prefix) => pathname?.startsWith(prefix));
}

export default function PublicShell({ children }) {
  const pathname = usePathname();
  const showChrome = isPublicRoute(pathname);

  return (
    <>
      {showChrome && <Navbar />}
      {children}
      {showChrome && <Footer />}
    </>
  );
}
