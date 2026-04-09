"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { OperazioniAttachmentPreviewDialog } from "@/components/operazioni/attachment-preview-dialog";
import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
  OperazioniInfoGrid,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { downloadAttachment, getAttachmentPreviewData, getReport, getReportAttachments } from "@/features/operazioni/api/client";

function SegnalazioneDetailContent({ reportId, context }: { reportId: string; context: string | null }) {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [attachments, setAttachments] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewState, setPreviewState] = useState<{ title: string; url: string | null; mimeType: string; textContent?: string | null } | null>(null);

  const loadReport = useCallback(async () => {
    try {
      const data = await getReport(reportId);
      const attachmentsData = await getReportAttachments(reportId).catch(() => []);
      setReport(data);
      setAttachments(Array.isArray(attachmentsData) ? attachmentsData : []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento segnalazione");
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  useEffect(() => {
    return () => {
      if (previewState?.url) {
        URL.revokeObjectURL(previewState.url);
      }
    };
  }, [previewState]);

  async function openAttachmentPreview(attachment: Record<string, unknown>) {
    try {
      if (previewState?.url) {
        URL.revokeObjectURL(previewState.url);
      }
      const data = await getAttachmentPreviewData(String(attachment.id));
      const url = data.textContent != null ? null : URL.createObjectURL(data.blob);
      setPreviewState({
        title: String(attachment.original_filename ?? data.filename ?? "Allegato"),
        url,
        mimeType: data.mimeType,
        textContent: data.textContent ?? null,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore anteprima allegato");
    }
  }

  function closePreview() {
    if (previewState?.url) {
      URL.revokeObjectURL(previewState.url);
    }
    setPreviewState(null);
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento segnalazione in corso...</p>;
  }

  if (error || !report) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Segnalazione non trovata"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Segnalazioni", href: "/operazioni/segnalazioni" },
          { label: String(report.report_number ?? "Dettaglio") },
        ]}
      />

      <OperazioniDetailHero
        eyebrow="Field report"
        title={String(report.title ?? "Segnalazione")}
        description="Scheda di lettura rapida per numero segnalazione, stato corrente e collegamento alla pratica interna."
        status={String(report.status ?? "submitted")}
        statusTone="bg-amber-50 text-amber-700"
      >
        {report.internal_case_id != null ? (
          <OperazioniHeroNotice
            title="Pratica collegata"
            description={`La segnalazione e gia agganciata alla pratica ${String(report.internal_case_id)}.`}
          />
        ) : (
          <OperazioniHeroNotice
            title="Da collegare"
            description="Questa segnalazione non risulta ancora agganciata a una pratica interna."
          />
        )}
      </OperazioniDetailHero>

      <OperazioniCollectionPanel
        title="Metadati segnalazione"
        description="Riferimenti base per numero, data apertura e allineamento con la pratica interna."
        count={6}
      >
        <OperazioniInfoGrid
          items={[
            { label: "Numero", value: String(report.report_number ?? "—") },
            {
              label: "Data creazione",
              value: report.created_at ? new Date(report.created_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Pratica",
              value:
                report.internal_case_id != null ? (
                  <Link href={`/operazioni/pratiche/${report.internal_case_id as string}${context === "miniapp" ? "?context=miniapp" : ""}`} className="text-[#1D4E35] hover:underline">
                    Apri pratica collegata
                  </Link>
                ) : (
                  "Non collegata"
                ),
            },
            { label: "Operatore", value: report.reporter_user_id ? `ID ${String(report.reporter_user_id)}` : "—" },
            { label: "Team", value: report.team_id ? `ID ${String(report.team_id)}` : "—" },
            { label: "Mezzo", value: report.vehicle_id ? `ID ${String(report.vehicle_id)}` : "—" },
          ]}
        />
        {report.description ? (
          <div className="mt-4 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-4 text-sm text-gray-700">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Descrizione</p>
            <p className="mt-2 leading-6">{String(report.description)}</p>
          </div>
        ) : null}
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Contesto operativo"
        description="Coordinate, attività correlata e metadati di ricezione disponibili sulla segnalazione."
        count={5 + attachments.length}
      >
        <OperazioniInfoGrid
          items={[
            {
              label: "Attività collegata",
              value: report.operator_activity_id ? (
                <Link href={`/operazioni/attivita/${String(report.operator_activity_id)}${context === "miniapp" ? "?context=miniapp" : ""}`} className="text-[#1D4E35] hover:underline">
                  Apri attività collegata
                </Link>
              ) : "Non collegata",
            },
            {
              label: "Latitudine",
              value: report.latitude != null ? String(report.latitude) : "—",
            },
            {
              label: "Longitudine",
              value: report.longitude != null ? String(report.longitude) : "—",
            },
            {
              label: "Accuratezza GPS",
              value: report.gps_accuracy_meters != null ? `${String(report.gps_accuracy_meters)} m` : "—",
            },
            {
              label: "Ricezione server",
              value: report.server_received_at ? new Date(report.server_received_at as string).toLocaleString("it-IT") : "—",
            },
          ]}
        />
        {attachments.length > 0 ? (
          <div className="mt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Allegati</p>
            <div className="mt-3 space-y-3">
              {attachments.map((attachment) => (
                <div key={String(attachment.id)} className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-gray-900">{String(attachment.original_filename ?? "Allegato")}</p>
                      <p className="mt-1 truncate text-xs leading-5 text-gray-500">
                        {String(attachment.mime_type ?? "tipo sconosciuto")}
                        {attachment.file_size_bytes != null ? ` · ${String(attachment.file_size_bytes)} bytes` : ""}
                      </p>
                    </div>
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600">
                      {String(attachment.attachment_type ?? "file")}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() =>
                        void openAttachmentPreview(attachment)
                      }
                    >
                      Anteprima
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() =>
                        void downloadAttachment(
                          String(attachment.id),
                          String(attachment.original_filename ?? "attachment"),
                        ).catch((e) =>
                          setError(e instanceof Error ? e.message : "Errore download allegato"),
                        )
                      }
                    >
                      Scarica
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Percorso operatore"
        description="Navigazione rapida per rientrare nella mini-app o continuare sulla pratica generata."
        count={report.internal_case_id != null ? (context === "miniapp" ? 3 : 2) : context === "miniapp" ? 2 : 1}
      >
        <div className="flex flex-wrap gap-3">
          {report.internal_case_id != null ? (
            <Link href={`/operazioni/pratiche/${report.internal_case_id as string}${context === "miniapp" ? "?context=miniapp" : ""}`} className="btn-primary">
              Apri pratica collegata
            </Link>
          ) : null}
          {context === "miniapp" ? (
            <Link href="/operazioni/miniapp/liste" className="btn-secondary">
              Torna a liste personali
            </Link>
          ) : null}
          <Link href="/operazioni/miniapp" className="btn-secondary">
            Apri mini-app
          </Link>
        </div>
      </OperazioniCollectionPanel>

      <div className="flex flex-wrap gap-3">
        <Link href="/operazioni/segnalazioni" className="btn-secondary">
          Torna alla lista segnalazioni
        </Link>
        {context === "miniapp" ? (
          <Link href="/operazioni/miniapp/liste" className="btn-secondary">
            Liste personali
          </Link>
        ) : null}
      </div>
      <OperazioniAttachmentPreviewDialog
        open={previewState != null}
        title={previewState?.title ?? "Anteprima allegato"}
        url={previewState?.url ?? null}
        mimeType={previewState?.mimeType ?? null}
        textContent={previewState?.textContent ?? null}
        onClose={closePreview}
      />
    </div>
  );
}

export default function SegnalazioneDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const context = searchParams.get("context");
  return (
    <OperazioniModulePage
      title="Dettaglio segnalazione"
      description="Contenuto, allegati e collegamento alla pratica."
      breadcrumb={`ID ${params.id}`}
    >
      {() => <SegnalazioneDetailContent reportId={params.id} context={context} />}
    </OperazioniModulePage>
  );
}
