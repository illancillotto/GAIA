"use client";

import { useEffect, useState } from "react";

import { RiordinoModulePage } from "@/components/riordino/module-page";
import { RiordinoPracticeTable } from "@/components/riordino/practice-list/practice-table";
import { getStoredAccessToken } from "@/lib/auth";

export default function RiordinoPracticesPage() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <RiordinoModulePage
      title="Pratiche Riordino"
      description="Elenco pratiche del modulo Riordino."
      breadcrumb="Riordino"
    >
      {token ? <RiordinoPracticeTable token={token} /> : <p className="text-sm text-gray-500">Caricamento sessione...</p>}
    </RiordinoModulePage>
  );
}
