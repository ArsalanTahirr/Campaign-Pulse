'use client';

import "./globals.css";
import { Inter } from "next/font/google";
import { usePathname } from "next/navigation";
import ThemeProvider from "@/components/providers/ThemeProvider";
import AppToaster from "@/components/providers/AppToaster";
import Navbar from "@/components/landing/Navbar";
import Footer from "@/components/landing/Footer";

const inter = Inter({ subsets: ["latin"] });

// This prevents metadata export error, but client-side pages can't export metadata
// Metadata is handled at page level instead
// export const metadata = {
//   title: "CampaignPulse",
//   description: "CampaignPulse helps teams automate cold email outreach with confidence.",
//   icons: {
//     icon: "/icon.png",
//     shortcut: "/icon.png",
//     apple: "/icon.png"
//   }
// };

export default function RootLayout({ children }) {
  const pathname = usePathname();
  const isLandingPage = pathname === '/';

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>CampaignPulse</title>
        <meta name="description" content="CampaignPulse helps teams automate cold email outreach with confidence." />
        <link rel="icon" href="/icon.png" />
        <link rel="shortcut icon" href="/icon.png" />
        <link rel="apple-touch-icon" href="/icon.png" />
      </head>
      <body className={`${inter.className} transition-colors duration-300`}>
        <ThemeProvider>
          {isLandingPage && <Navbar />}
          {children}
          {isLandingPage && <Footer />}
          <AppToaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
