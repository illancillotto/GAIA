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
import {
  acknowledgeCase,
  assignCase,
  closeCase,
  downloadAttachment,
  getAttachmentPreviewData,
  getCase,
  getCaseAttachments,
  getCaseEvents,
  reopenCase,
  resolveCase,
  startCase,
} from "@/features/operazioni/api/client";

const statusLabels: Record<string, string> = {
  open: "Aperta",
  assigned: "Assegnata",
  acknowledged: "Presa in carico",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiusa",
  cancelled: "Annullata",
  reopened: "Riaperta",
};

const statusTone: Record<string, string> = {
  open: "bg-sky-50 text-sky-700",
  assigned: "bg-indigo-50 text-indigo-700",
  acknowledged: "bg-purple-50 text-purple-700",
  in_progress: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  closed: "bg-gray-100 text-gray-600",
  cancelled: "bg-rose-50 text-rose-700",
  reopened: "bg-orange-50 text-orange-700",
};

function PraticaDetailContent({ caseId, currentUserId, context }: { caseId: string; currentUserId: number; context: string | null }) {
  const [caseData, setCaseData] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [attachments, setAttachments] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionNote, setActionNote] = useState("");
  const [previewState, setPreviewState] = useState<{ title: string; url: string | null; mimeType: string; textContent?: string | null } | null>(null);

  const loadCase = useCallback(async () => {
    try {
      const [data, eventsData, attachmentsData] = await Promise.all([
        getCase(caseId),
        getCaseEvents(caseId).catch(() => []),
        getCaseAttachments(caseId).catch(() => []),
      ]);
      setCaseData(data);
      setEvents(Array.isArray(eventsData) ? eventsData : []);
      setAttachments(Array.isArray(attachmentsData) ? attachmentsData : []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento pratica");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    void loadCase();
  }, [loadCase]);

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

  async function runCaseAction(action: "assign" | "acknowledge" | "start" | "resolve" | "close" | "reopen") {
    try {
      setIsSubmitting(true);
      const notePayload =
        action === "resolve" || action === "close"
          ? { resolution_note: actionNote, note: actionNote }
          : { note: actionNote };

      if (action === "assign") {
        await assignCase(caseId, { assigned_to_user_id: currentUserId, ...notePayload });
      } else if (action === "acknowledge") {
        await acknowledgeCase(caseId, notePayload);
      } else if (action === "start") {
        await startCase(caseId, notePayload);
      } else if (action === "resolve") {
        await resolveCase(caseId, notePayload);
      } else if (action === "close") {
        await closeCase(caseId, notePayload);
      } else {
        await reopenCase(caseId, notePayload);
      }

      setActionNote("");
      await loadCase();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore aggiornamento pratica");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento pratica in corso...</p>;
  }

  if (error || !caseData) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Pratica non trovata"}</p>
      </article>
    );
  }

  const sourceReportId = String((caseData.source_report as Record<string, unknown> | undefined)?.id ?? "");

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Pratiche", href: "/operazioni/pratiche" },
          { label: String(caseData.case_number ?? "Dettaglio") },
        ]}
      />

      <OperazioniDetailHero
        eyebrow="Case workflow"
        title={String(caseData.title ?? "Pratica")}
        description={String(caseData.description ?? "Scheda pratica con stato corrente, classificazione e cronologia eventi operativi.")}
        status={statusLabels[String(caseData.status)] || String(caseData.status)}
        statusTone={statusTone[String(caseData.status)] || "bg-gray-100 text-gray-600"}
      >
        <OperazioniHeroNotice
          title="Segnalazione sorgente"
          description={String((caseData.source_report as Record<string, unknown>)?.report_number ?? "Nessuna segnalazione collegata.")}
        />
      </OperazioniDetailHero>

      <OperazioniCollectionPanel
        title="Classificazione pratica"
        description="Informazioni di contesto utili per assegnazione, priorita e lettura amministrativa."
        count={8}
      >
        <OperazioniInfoGrid
          items={[
            { label: "Numero pratica", value: String(caseData.case_number ?? "—") },
            { label: "Categoria", value: String((caseData.category as Record<string, unknown>)?.name ?? "—") },
            { label: "Gravita", value: String((caseData.severity as Record<string, unknown>)?.name ?? "—") },
            { label: "Segnalazione", value: String((caseData.source_report as Record<string, unknown>)?.report_number ?? "—") },
            { label: "Assegnata a", value: caseData.assigned_to_user_id ? `ID ${String(caseData.assigned_to_user_id)}` : "Non assegnata" },
            { label: "Team assegnato", value: caseData.assigned_team_id ? `ID ${String(caseData.assigned_team_id)}` : "—" },
            { label: "Priorità", value: caseData.priority_rank != null ? String(caseData.priority_rank) : "—" },
            { label: "Creazione", value: caseData.created_at ? new Date(caseData.created_at as string).toLocaleString("it-IT") : "—" },
          ]}
        />
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Percorso operatore"
        description="Shortcut per il flusso mini-app e per tornare alla segnalazione sorgente senza passare dalla console desktop."
        count={(sourceReportId ? 1 : 0) + (context === "miniapp" ? 1 : 0) + 1}
      >
        <div className="flex flex-wrap gap-3">
          {sourceReportId ? (
            <Link
              href={`/operazioni/segnalazioni/${sourceReportId}${context === "miniapp" ? "?context=miniapp" : ""}`}
              className="btn-secondary"
            >
              Apri segnalazione sorgente
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

      <OperazioniCollectionPanel
        title="Cronologia eventi"
        description="Timeline completa degli eventi registrati sulla pratica."
        count={events.length}
      >

        {events.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun evento registrato.</p>
        ) : (
          <div className="space-y-3">
            {events.map((event, idx) => (
              <div key={idx} className="flex gap-3 text-sm">
                <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-gray-400" />
                <div>
                  <p className="font-medium text-gray-700">{String(event.event_type)}</p>
                  <p className="text-xs text-gray-500">
                    {event.event_at ? new Date(event.event_at as string).toLocaleString("it-IT") : ""}
                    {event.note ? ` — ${String(event.note)}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Tappe workflow"
        description="Marcatori temporali principali per presa in carico, lavorazione, risoluzione e chiusura."
        count={4 + attachments.length}
      >
        <OperazioniInfoGrid
          items={[
            {
              label: "Presa in carico",
              value: caseData.acknowledged_at ? new Date(caseData.acknowledged_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Avvio lavorazione",
              value: caseData.started_at ? new Date(caseData.started_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Risoluzione",
              value: caseData.resolved_at ? new Date(caseData.resolved_at as string).toLocaleString("it-IT") : "—",
            },
            {
              label: "Chiusura",
              value: caseData.closed_at ? new Date(caseData.closed_at as string).toLocaleString("it-IT") : "—",
            },
          ]}
        />
        {caseData.resolution_note ? (
          <div className="mt-4 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-4 text-sm text-gray-700">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Nota di risoluzione</p>
            <p className="mt-2 leading-6">{String(caseData.resolution_note)}</p>
          </div>
        ) : null}
        {attachments.length > 0 ? (
          <div className="mt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Allegati pratica</p>
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
        title="Azioni pratica"
        description="Transizioni di stato disponibili in base alla fase corrente del workflow."
        count={["closed", "resolved"].includes(String(caseData.status)) ? 2 : 4}
      >
        <label className="block">
          <span className="label-caption">Nota operativa</span>
          <textarea
            className="form-control mt-2 min-h-24"
            value={actionNote}
            onChange={(event) => setActionNote(event.target.value)}
            placeholder="Aggiungi una nota per assegnazione, presa in carico o chiusura"
          />
        </label>
        <div className="mt-4 flex flex-wrap gap-3">
          {String(caseData.status) === "open" ? (
            <button type="button" className="btn-secondary" disabled={isSubmitting} onClick={() => void runCaseAction("assign")}>
              {isSubmitting ? "Invio..." : "Assegna a me"}
            </button>
          ) : null}
          {String(caseData.status) === "assigned" ? (
            <button type="button" className="btn-secondary" disabled={isSubmitting} onClick={() => void runCaseAction("acknowledge")}>
              {isSubmitting ? "Invio..." : "Prendi in carico"}
            </button>
          ) : null}
          {["assigned", "acknowledged", "reopened"].includes(String(caseData.status)) ? (
            <button type="button" className="btn-secondary" disabled={isSubmitting} onClick={() => void runCaseAction("start")}>
              {isSubmitting ? "Invio..." : "Avvia lavorazione"}
            </button>
          ) : null}
          {["in_progress", "reopened"].includes(String(caseData.status)) ? (
            <button type="button" className="btn-secondary" disabled={isSubmitting} onClick={() => void runCaseAction("resolve")}>
              {isSubmitting ? "Invio..." : "Risolvi"}
            </button>
          ) : null}
          {["resolved", "in_progress"].includes(String(caseData.status)) ? (
            <button type="button" className="btn-primary" disabled={isSubmitting} onClick={() => void runCaseAction("close")}>
              {isSubmitting ? "Invio..." : "Chiudi pratica"}
            </button>
          ) : null}
          {["closed", "resolved"].includes(String(caseData.status)) ? (
            <button type="button" className="btn-secondary" disabled={isSubmitting} onClick={() => void runCaseAction("reopen")}>
              {isSubmitting ? "Invio..." : "Riapri"}
            </button>
          ) : null}
        </div>
      </OperazioniCollectionPanel>

      <div className="flex flex-wrap gap-3">
        <Link href="/operazioni/pratiche" className="btn-secondary">
          Torna alla lista pratiche
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

export default function PraticaDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const context = searchParams.get("context");
  return (
    <OperazioniModulePage
      title="Dettaglio pratica"
      description="Stato, assegnazioni e timeline della pratica."
      breadcrumb={`ID ${params.id}`}
    >
      {({ currentUser }) => <PraticaDetailContent caseId={params.id} currentUserId={currentUser.id} context={context} />}
    </OperazioniModulePage>
  );
}
