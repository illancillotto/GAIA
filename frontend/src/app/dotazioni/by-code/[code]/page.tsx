"use client";

import { useParams } from "next/navigation";
import { ProtectedPage } from "@/components/app/protected-page";
import { AssetDetail } from "@/features/dotazioni/AssetDetail";

export default function DotazioneCodePage() {
  const params = useParams<{ code: string }>();
  return <ProtectedPage title="Dotazione da QR" description="Consultazione autenticata del bene." breadcrumbItems={[{ label: "Dotazioni", href: "/dotazioni" }, { label: params.code }]} requiredModule="dotazioni" requiredSection="dotazioni.view">
    <AssetDetail code={params.code} />
  </ProtectedPage>;
}
