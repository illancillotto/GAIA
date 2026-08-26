"use client";

import { ProtectedPage } from "@/components/app/protected-page";
import { getStoredAccessToken } from "@/lib/auth";

import { GisAdministrationWorkspace } from "./administration-workspace";

export default function GisAdministrationPage() {
  return (
    <ProtectedPage
      title="Amministrazione GIS"
      description="Configura layer, disponibilità, export e governance QGIS."
      breadcrumb="GIS Platform / Amministrazione"
      requiredModule="gis"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="gis-touch-targets">
        <GisAdministrationWorkspace token={getStoredAccessToken()} />
      </div>
    </ProtectedPage>
  );
}
