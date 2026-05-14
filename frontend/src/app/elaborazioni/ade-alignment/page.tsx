import { Suspense } from "react";

import { ElaborazioniAdeAlignmentWorkspace } from "@/components/elaborazioni/ade-alignment-workspace";

export default function ElaborazioniAdeAlignmentPage() {
  return (
    <Suspense fallback={null}>
      <ElaborazioniAdeAlignmentWorkspace />
    </Suspense>
  );
}
