import "./globals.css";

export const metadata = {
  title: "CampaignPulse",
  description: "CampaignPulse helps teams automate cold email outreach with confidence.",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png"
  }
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
