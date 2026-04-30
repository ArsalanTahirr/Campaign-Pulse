import DashboardShell from "@/components/dashboard/DashboardShell";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";

export default function DashboardLayout({ children }) {
  return (
    <WorkspaceProvider>
      <DashboardShell>{children}</DashboardShell>
    </WorkspaceProvider>
  );
}
