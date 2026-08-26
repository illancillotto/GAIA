"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { getStoredAccessToken } from "@/lib/auth";

import { GisToolsWorkspace } from "./tools-workspace";

export default function GisToolsPage() {
  return (
    <ProtectedPage
      title="Strumenti GIS"
      description="Import guidati, attività persistenti e strumenti QGIS per operatori esperti."
      breadcrumb="GIS Platform / Strumenti"
      requiredModule="gis"
    >
      <div className="gis-touch-targets">
        <GisToolsWorkspace token={getStoredAccessToken()} />
      </div>
    </ProtectedPage>
  );
}
