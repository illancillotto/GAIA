"use client";

import { useEffect, useState } from "react";

import { RiordinoModulePage } from "@/components/riordino/module-page";
import { RiordinoDashboardOverview } from "@/components/riordino/dashboard/dashboard-overview";
import { getStoredAccessToken } from "@/lib/auth";

export default function RiordinoPage() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <RiordinoModulePage
      title="GAIA Riordino"
      description="Dashboard del modulo di riordino catastale."
    >
      {token ? <RiordinoDashboardOverview token={token} /> : <p className="text-sm text-gray-500">Caricamento sessione...</p>}
    </RiordinoModulePage>
  );
}
