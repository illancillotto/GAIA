"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";

import { useParticellaDetailColumns } from "./particella-detail-columns";
import { particellaReference } from "./particella-detail-helpers";
import { AnomaliePanel, HistoryPanel, SubjectQuickView, UtenzePanel } from "./particella-related-sections";
import { ConsorzioPanel, ParticellaSummaryPanel } from "./particella-summary-sections";
import { useParticellaDetailController } from "./use-particella-detail-controller";

export default function CatastoParticellaDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const controller = useParticellaDetailController(params.id);
  const columns = useParticellaDetailColumns({
    capacitasLinkBusy: controller.capacitasLinkBusy,
    consorzio: controller.consorzio,
    subjectLookupBusyId: controller.subjectLookupBusyId,
    onOpenCertificato: controller.openCapacitasCertificato,
    onOpenSubject: controller.openSubjectQuickView,
    onUpdateAnomalia: controller.updateAnomalia,
  });
  const reference = particellaReference(controller.item);

  return (
    <CatastoPage
      title={reference}
      description="Scheda particella con dati catastali, anagrafica collegata e storico SCD2."
      breadcrumb="Catasto / Particelle / Dettaglio"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {searchParams.get("embedded") === "1" ? <div className="flex justify-start"><button type="button" className="btn-secondary" onClick={() => router.back()}>Indietro</button></div> : null}
        {controller.error ? <AlertBanner variant="danger" title="Errore caricamento">{controller.error}</AlertBanner> : null}
        <ParticellaSummaryPanel item={controller.item} isLoading={controller.isLoading} reference={reference} syncBusy={controller.syncBusy} syncMessage={controller.syncMessage} onSync={controller.syncParticella} />
        <ConsorzioPanel consorzio={controller.consorzio} isLoading={controller.isLoading} columns={columns.occupancies} />
        <UtenzePanel
          anno={controller.anno}
          capacitasLinkError={controller.capacitasLinkError}
          columns={columns.utenze}
          isLoading={controller.isLoading}
          subjectLookupError={controller.subjectLookupError}
          utenze={controller.utenze}
          onAnnoChange={controller.setAnno}
        />
        <AnomaliePanel anomalie={controller.anomalie} columns={columns.anomalie} isLoading={controller.isLoading} />
        <HistoryPanel columns={columns.history} history={controller.history} isLoading={controller.isLoading} />
        <SubjectQuickView selectedSubjectId={controller.selectedSubjectId} utenze={controller.utenze} onClose={() => controller.setSelectedSubjectId(null)} />
      </div>
    </CatastoPage>
  );
}
