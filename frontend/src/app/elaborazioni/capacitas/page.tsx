"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";

function ElaborazioniCapacitasPageContent() {
  const searchParams = useSearchParams();
  const requestedSection = searchParams.get("section");
  const initialSection =
    requestedSection === "particelle" ||
    requestedSection === "storico" ||
    requestedSection === "terreni" ||
    requestedSection === "certificati" ||
    requestedSection === "anomalie" ||
    requestedSection === "incass"
      ? requestedSection
      : "particelle";

  return <ElaborazioniCapacitasWorkspace initialSection={initialSection} />;
}

export default function ElaborazioniCapacitasPage() {
  return (
    <Suspense fallback={null}>
      <ElaborazioniCapacitasPageContent />
    </Suspense>
  );
}
