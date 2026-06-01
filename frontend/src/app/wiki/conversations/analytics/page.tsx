import { ProtectedPage } from "@/components/app/protected-page";
import { WikiConversationsAnalyticsPage } from "@/features/wiki/WikiConversationsAnalyticsPage";

export const metadata = {
  title: "Analytics Conversazioni Wiki — GAIA",
  description: "Trend e breakdown storici della coda conversazioni del Wiki Agent.",
};

export default function WikiConversationsAnalyticsRoute() {
  return (
    <ProtectedPage
      title="Analytics conversazioni Wiki"
      description="Serie storiche, backlog e tempi medi della coda conversazioni del Wiki Agent."
      breadcrumb="GAIA / Wiki / Conversazioni / Analytics"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiConversationsAnalyticsPage />
    </ProtectedPage>
  );
}
