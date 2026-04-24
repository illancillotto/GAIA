import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { Suspense } from "react";

export default function ElaborazioniCapacitasPage() {
  return (
    <Suspense fallback={null}>
      <ElaborazioniCapacitasWorkspace />
    </Suspense>
  );
}
