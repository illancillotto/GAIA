"use client";

import { use, useEffect, useState } from "react";

import { RiordinoModulePage } from "@/components/riordino/module-page";
import { RiordinoPracticeDetailView } from "@/components/riordino/practice-detail/practice-detail-view";
import { getStoredAccessToken } from "@/lib/auth";

export default function RiordinoPracticeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <RiordinoModulePage
      title="Dettaglio pratica Riordino"
      description="Workspace sintetico della pratica di riordino selezionata."
      breadcrumb="Riordino / Pratiche"
    >
      {token ? (
        <RiordinoPracticeDetailView token={token} practiceId={id} />
      ) : (
        <p className="text-sm text-gray-500">Caricamento sessione...</p>
      )}
    </RiordinoModulePage>
  );
}
