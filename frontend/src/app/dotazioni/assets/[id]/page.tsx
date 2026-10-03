"use client";

import { useParams } from "next/navigation";
import { ProtectedPage } from "@/components/app/protected-page";
import { AssetDetail } from "@/features/dotazioni/AssetDetail";

export default function DotazionePage() {
  const params = useParams<{ id: string }>();
  return <ProtectedPage title="Dettaglio dotazione" description="Assegnazione, custodia e storico." breadcrumbItems={[{ label: "Dotazioni", href: "/dotazioni" }, { label: "Dettaglio" }]} requiredModule="dotazioni" requiredSection="dotazioni.view">
    <AssetDetail id={params.id} />
  </ProtectedPage>;
}
