import { ProtectedPage } from "@/components/app/protected-page";
import { WikiTelemetryPage } from "@/features/wiki/WikiTelemetryPage";

export const metadata = {
  title: "Telemetria Wiki — GAIA",
  description: "Trend storici e osservabilità del Wiki Agent.",
};

export default function WikiTelemetryRoute() {
  return (
    <ProtectedPage
      title="Telemetria Wiki"
      description="KPI storici, trend e breakdown del Wiki Agent per audit, fallback e mode operative."
      breadcrumb="GAIA / Wiki / Telemetria"
      requiredRoles={["admin", "super_admin"]}
    >
      <WikiTelemetryPage />
    </ProtectedPage>
  );
}
