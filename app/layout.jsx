import "./globals.css";
import { Inter } from "next/font/google";
import ThemeProvider from "@/components/providers/ThemeProvider";
import AppToaster from "@/components/providers/AppToaster";
import PublicShell from "@/components/providers/PublicShell";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "CampaignPulse",
  description: "CampaignPulse helps teams automate cold email outreach with confidence.",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} transition-colors duration-300`}>
        <ThemeProvider>
          <PublicShell>
            {children}
          </PublicShell>
          <AppToaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
