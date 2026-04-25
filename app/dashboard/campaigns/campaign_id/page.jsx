import CampaignDetailView from "@/components/dashboard/CampaignDetailView";

export const metadata = {
  title: "Campaign — Campaign Pulse",
};

export default function CampaignDetailPage({ params }) {
  return <CampaignDetailView campaignId={params.campaign_id} />;
}
