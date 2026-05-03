import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import SocialProof from "@/components/landing/SocialProof";

export const metadata = {
  title: "CampaignPulse",
  description: "CampaignPulse helps teams automate cold email outreach with confidence.",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png"
  }
};

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      <Hero />
      <Features />
      <SocialProof />
    </main>
  );
}
