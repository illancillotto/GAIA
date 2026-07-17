"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RiordinoBlockDetailView } from "@/components/riordino/blocks/block-detail-view";
import { RiordinoModulePage } from "@/components/riordino/module-page";
import { getStoredAccessToken } from "@/lib/auth";

export default function RiordinoBlockDetailPage() {
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <RiordinoModulePage
      title="Blocco Riordino"
      description="Workspace operativo del blocco con particelle, confronti e audit."
      breadcrumb="Riordino / Blocchi"
    >
      {token ? <RiordinoBlockDetailView token={token} blockId={params.id} /> : <p className="text-sm text-gray-500">Caricamento sessione...</p>}
    </RiordinoModulePage>
  );
}
