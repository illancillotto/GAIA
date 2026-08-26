"use client";

import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { getStoredAccessToken } from "@/lib/auth";

import { GisLayerDetailWorkspace } from "./layer-detail-workspace";

export default function GisLayerDetailPage() {
  const params = useParams<{ layerId: string }>();
  const token = getStoredAccessToken();
  return (
    <ProtectedPage
      title="Dettaglio mappa"
      description="Consulta la mappa e le informazioni essenziali del layer selezionato."
      breadcrumb="GIS Platform / Catalogo / Mappa"
      requiredModule="gis"
    >
      <div className="gis-touch-targets">
        <GisLayerDetailWorkspace token={token} layerId={params.layerId} />
      </div>
    </ProtectedPage>
  );
}
