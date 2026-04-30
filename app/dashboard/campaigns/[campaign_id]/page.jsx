import CampaignDetailView from "@/components/dashboard/CampaignDetailView";

export const metadata = {
  title: "Campaign — Campaign Pulse",
};

export default async function CampaignDetailPage({ params }) {
  const { campaign_id } = await params;
  return <CampaignDetailView campaignId={campaign_id} />;
}
