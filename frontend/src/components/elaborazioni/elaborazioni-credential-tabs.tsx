"use client";

import { useEffect, useState } from "react";

import { PresenzeCredentialVault } from "@/components/presenze/presenze-credential-vault";

export type ElaborazioniCredentialTab = "sister" | "whitecompany" | "capacitas" | "presenze";

const CREDENTIAL_TABS: Array<{ id: ElaborazioniCredentialTab; label: string }> = [
  { id: "sister", label: "SISTER" },
  { id: "whitecompany", label: "WhiteCompany" },
  { id: "capacitas", label: "Capacitas" },
  { id: "presenze", label: "Presenze INAZ" },
];

const PRESENZE_TAB_HASH = "#credenziali-inaz";

export function useOpenSection(initial = true): readonly [boolean, () => void] {
  const [open, setOpen] = useState(initial);
  function toggle() {
    setOpen((current) => !current);
  }
  return [open, toggle];
}

export function useElaborazioniCredentialTab(): readonly [
  ElaborazioniCredentialTab,
  (tab: ElaborazioniCredentialTab) => void,
] {
  const [activeTab, setActiveTab] = useState<ElaborazioniCredentialTab>("sister");
  useEffect(() => {
    if (window.location.hash === PRESENZE_TAB_HASH) setActiveTab("presenze");
  }, []);
  return [activeTab, setActiveTab];
}

export function selectCredentialTab(
  tab: ElaborazioniCredentialTab,
  onChange: (tab: ElaborazioniCredentialTab) => void,
): void {
  onChange(tab);
  const nextUrl = tab === "presenze" ? PRESENZE_TAB_HASH : `${window.location.pathname}${window.location.search}`;
  window.history.replaceState(null, "", nextUrl);
}

export function ElaborazioniCredentialTabs({
  activeTab,
  embedded,
  onChange,
}: {
  activeTab: ElaborazioniCredentialTab;
  embedded: boolean;
  onChange: (tab: ElaborazioniCredentialTab) => void;
}) {
  return (
    <>
      <div
        className={`flex flex-wrap rounded-[22px] border border-[#d9dfd6] bg-white shadow-panel ${
          embedded ? "gap-2 p-2" : "gap-2.5 p-2.5"
        }`}
      >
        {CREDENTIAL_TABS.map((tab) => (
          <button
            className={`rounded-2xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.id ? "bg-[#1D4E35] text-white" : "bg-gray-50 text-gray-700 hover:bg-gray-100"
            }`}
            id={tab.id === "presenze" ? "credenziali-inaz" : undefined}
            key={tab.id}
            onClick={() => selectCredentialTab(tab.id, onChange)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "presenze" ? <PresenzeCredentialVault /> : null}
    </>
  );
}
