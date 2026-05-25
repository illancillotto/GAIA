"use client";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

export default function ElaborazioniCapacitasPage() {
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

  return (
    <Suspense fallback={null}>
      <ElaborazioniCapacitasWorkspace initialSection={initialSection} />
    </Suspense>
  );
}
