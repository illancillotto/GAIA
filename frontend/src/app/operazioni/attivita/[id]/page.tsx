"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { OperazioniAttachmentPreviewDialog } from "@/components/operazioni/attachment-preview-dialog";
import { OperazioniGpsTrackViewerDialog } from "@/components/operazioni/gps-track-viewer-dialog";
import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
  OperazioniInfoGrid,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import {
  downloadAttachment,
  getActivity,
  getActivityAttachments,
  getActivityGpsSummary,
  getActivityGpsViewer,
  getAttachmentPreviewData,
} from "@/features/operazioni/api/client";

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  submitted: "Inviata",
  under_review: "In revisione",
  approved: "Approvata",
  rejected: "Respinta",
};

const statusTone: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  in_progress: "bg-sky-50 text-sky-700",
  submitted: "bg-amber-50 text-amber-700",
  under_review: "bg-purple-50 text-purple-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

function AttivitaDetailContent({ activityId, context }: { activityId: string; context: string | null }) {
  const [activity, setActivity] = useState<Record<string, unknown> | null>(null);
  const [attachments, setAttachments] = useState<Record<string, unknown>[]>([]);
  const [gpsSummary, setGpsSummary] = useState<Record<string, unknown> | null>(null);
  const [gpsViewer, setGpsViewer] = useState<Record<string, unknown> | null>(null);
  const [gpsViewerOpen, setGpsViewerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewState, setPreviewState] = useState<{ title: string; url: string | null; mimeType: string; textContent?: string | null } | null>(null);

  const loadActivity = useCallback(async () => {
    try {
      const data = await getActivity(activityId);
      const [attachmentsData, gpsData] = await Promise.all([
        getActivityAttachments(activityId).catch(() => []),
        getActivityGpsSummary(activityId).catch(() => null),
      ]);
      setActivity(data);
      setAttachments(Array.isArray(attachmentsData) ? attachmentsData : []);
      setGpsSummary(gpsData && typeof gpsData === "object" ? gpsData : null);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento attività");
    } finally {
      setLoading(false);
    }
  }, [activityId]);

  useEffect(() => {
    void loadActivity();
  }, [loadActivity]);

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

  async function openGpsViewer() {
    try {
      const data = await getActivityGpsViewer(activityId);
      if (!data) {
        setError("Viewer GPS non disponibile per questa attività");
        return;
      }
      setGpsViewer(data as Record<string, unknown>);
      setGpsViewerOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento viewer GPS");
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento attività in corso...</p>;
  }

  if (error || !activity) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Attività non trovata"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Attivita", href: "/operazioni/attivita" },
          { label: `ID ${String(activity.id).slice(0, 8)}` },
        ]}
      />

      <OperazioniDetailHero
        eyebrow="Workflow operatori"
        title={`Attivita ${String(activity.id).slice(0, 8)}…`}
        description="Scheda di presidio per tempi, stato, note operative e prossimi blocchi applicativi ancora da completare."
        status={statusLabels[String(activity.status)] || String(activity.status)}
        statusTone={statusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}
      >
        <OperazioniHeroNotice
          title="Lettura rapida"
          description={activity.operator_user_id ? `Assegnata all'operatore ${String(activity.operator_user_id)}.` : "Operatore non valorizzato."}
        />
      </OperazioniDetailHero>

      <OperazioniCollectionPanel
        title="Metadati attivita"
        description="Tempi operativi, utente assegnato e contenuto testuale associato alla sessione."
        count={6}
      >
        <OperazioniInfoGrid
          items={[
            {
              label: "Inizio",
              value: activity.started_at ? new Date(activity.started_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Fine",
              value: activity.ended_at ? new Date(activity.ended_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Operatore",
              value: activity.operator_user_id ? `ID ${activity.operator_user_id}` : "—",
            },
            {
              label: "Team",
              value: activity.team_id ? `ID ${String(activity.team_id)}` : "—",
            },
            {
              label: "Mezzo",
              value: activity.vehicle_id ? `ID ${String(activity.vehicle_id)}` : "—",
            },
            {
              label: "Durata",
              value: activity.duration_minutes_calculated != null ? `${String(activity.duration_minutes_calculated)} min` : activity.duration_minutes_declared != null ? `${String(activity.duration_minutes_declared)} min dichiarati` : "—",
            },
          ]}
        />
        {activity.text_note != null ? (
          <div className="mt-4 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-4 text-sm text-gray-700">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Note</p>
            <p className="mt-2 leading-6">{String(activity.text_note)}</p>
          </div>
        ) : null}
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Percorso operatore"
        description="Azioni rapide per restare nel flusso mini-app quando il dettaglio è aperto dal workset personale."
        count={context === "miniapp" ? 3 : 2}
      >
        <div className="flex flex-wrap gap-3">
          {String(activity.status) === "in_progress" ? (
            <Link href="/operazioni/miniapp/attivita/chiusura" className="btn-primary">
              Vai a chiusura attività
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

      <div className="grid gap-6 sm:grid-cols-2">
        <OperazioniCollectionPanel title="Tracking e note" description="Stadio di raccolta dati GPS, nota audio e marcatori di invio/revisione." count={gpsSummary ? 9 : 6}>
          <OperazioniInfoGrid
            items={[
              {
                label: "GPS summary",
                value: activity.gps_track_summary_id ? `ID ${String(activity.gps_track_summary_id)}` : "Non collegato",
              },
              {
                label: "Nota audio",
                value: activity.audio_note_attachment_id ? `Attachment ${String(activity.audio_note_attachment_id)}` : "Assente",
              },
              {
                label: "Ricezione server",
                value: activity.server_received_at ? new Date(activity.server_received_at as string).toLocaleString("it-IT") : "—",
              },
              {
                label: "Invio revisione",
                value: activity.submitted_at ? new Date(activity.submitted_at as string).toLocaleString("it-IT") : "Non inviato",
              },
              {
                label: "Distanza",
                value: gpsSummary?.total_distance_km != null ? `${String(gpsSummary.total_distance_km)} km` : "—",
              },
              {
                label: "Durata track",
                value: gpsSummary?.total_duration_seconds != null ? `${String(gpsSummary.total_duration_seconds)} sec` : "—",
              },
              {
                label: "Provider",
                value: gpsSummary?.provider_name ? String(gpsSummary.provider_name) : "—",
              },
              {
                label: "Start",
                value:
                  gpsSummary?.start_latitude != null && gpsSummary?.start_longitude != null
                    ? `${String(gpsSummary.start_latitude)}, ${String(gpsSummary.start_longitude)}`
                    : "—",
              },
              {
                label: "End",
                value:
                  gpsSummary?.end_latitude != null && gpsSummary?.end_longitude != null
                    ? `${String(gpsSummary.end_latitude)}, ${String(gpsSummary.end_longitude)}`
                    : "—",
              },
            ]}
          />
          {gpsSummary ? (
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" className="btn-secondary" onClick={() => void openGpsViewer()}>
                Apri viewer GPS
              </button>
            </div>
          ) : null}
        </OperazioniCollectionPanel>
        <OperazioniCollectionPanel title="Esito revisione e allegati" description="Informazioni di approvazione e materiali associati all'attività." count={3 + attachments.length}>
          <OperazioniInfoGrid
            items={[
              {
                label: "Esito",
                value: activity.review_outcome ? String(activity.review_outcome) : "Non revisionata",
              },
              {
                label: "Revisionata da",
                value: activity.reviewed_by_user_id ? `ID ${String(activity.reviewed_by_user_id)}` : "—",
              },
              {
                label: "Data revisione",
                value: activity.reviewed_at ? new Date(activity.reviewed_at as string).toLocaleString("it-IT") : "—",
              },
            ]}
          />
          {activity.review_note ? (
            <div className="mt-4 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-4 text-sm text-gray-700">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Nota revisione</p>
              <p className="mt-2 leading-6">{String(activity.review_note)}</p>
            </div>
          ) : null}
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
      </div>

      <div className="flex flex-wrap gap-3">
        <Link href="/operazioni/attivita" className="btn-secondary">
          Torna alla lista attività
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
      <OperazioniGpsTrackViewerDialog
        open={gpsViewerOpen}
        title={`Traccia attività ${String(activity.id).slice(0, 8)}…`}
        points={Array.isArray(gpsViewer?.points) ? (gpsViewer.points as { latitude: number; longitude: number; timestamp?: string | null }[]) : []}
        bounds={gpsViewer?.bounds && typeof gpsViewer.bounds === "object" ? (gpsViewer.bounds as { min_latitude: number | null; max_latitude: number | null; min_longitude: number | null; max_longitude: number | null }) : null}
        summary={gpsViewer?.summary && typeof gpsViewer.summary === "object" ? (gpsViewer.summary as Record<string, unknown>) : null}
        viewerMode={typeof gpsViewer?.viewer_mode === "string" ? gpsViewer.viewer_mode : null}
        usesRawPayload={Boolean(gpsViewer?.uses_raw_payload)}
        onClose={() => setGpsViewerOpen(false)}
      />
    </div>
  );
}

export default function AttivitaDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const context = searchParams.get("context");
  return (
    <OperazioniModulePage
      title="Dettaglio attività"
      description="Stato, tempi e metadati dell’attività operatore."
      breadcrumb={`ID ${params.id}`}
    >
      {() => <AttivitaDetailContent activityId={params.id} context={context} />}
    </OperazioniModulePage>
  );
}
