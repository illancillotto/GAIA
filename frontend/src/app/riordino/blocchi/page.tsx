"use client";

import { useEffect, useState } from "react";

import { RiordinoBlockList } from "@/components/riordino/blocks/block-list";
import { RiordinoModulePage } from "@/components/riordino/module-page";
import { getStoredAccessToken } from "@/lib/auth";

export default function RiordinoBlocksPage() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <RiordinoModulePage
      title="Blocchi Riordino"
      description="Dashboard dei blocchi operativi assegnati a coordinatori e operatori."
      breadcrumb="Riordino"
    >
      {token ? <RiordinoBlockList token={token} /> : <p className="text-sm text-gray-500">Caricamento sessione...</p>}
    </RiordinoModulePage>
  );
}
