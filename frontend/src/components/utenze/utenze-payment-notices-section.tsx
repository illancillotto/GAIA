"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, FolderIcon } from "@/components/ui/icons";
import { createCapacitasInCassSyncJob, getUtenzeSubjectPaymentNotices, listCapacitasInCassSyncJobs } from "@/lib/api";
import { isCapacitasInCassActiveJobStatus } from "@/lib/capacitas-incass-job-visibility";
import { buildNoticeResidualNotes, extractNoticeDetailFields, extractNoticeRateDetails } from "@/lib/utenze-payment-notice-detail";
import { buildPaymentNoticeSummary, getPaymentNoticeStatus, parseNoticeAmount } from "@/lib/utenze-payment-notices-summary";
import type { AnagraficaPaymentNotice, CapacitasInCassSyncJobListItem } from "@/types/api";

type Props = {
  subjectId: string;
  token: string;
  compact?: boolean;
};

const INCASS_JOB_POLL_MS = 3000;

function formatMoney(value: string | null | undefined): string {
  if (!value) return "—";
  const normalized = parseNoticeAmount(value);
  if (normalized == null || Number.isNaN(normalized)) return value;
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(normalized);
}

function formatMoneyNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function buildRateizationInsight(notice: AnagraficaPaymentNotice) {
  const rateizedAmount = parseNoticeAmount(notice.importo_rateizzato);
  if (rateizedAmount == null || rateizedAmount <= 0) {
    return null;
  }
  const issuedAmount = parseNoticeAmount(notice.importo_carico);
  const paidAmount = parseNoticeAmount(notice.importo_riscosso);
  const residualAmount = parseNoticeAmount(notice.importo_residuo);
  const feeAmount = issuedAmount == null ? null : Math.max(rateizedAmount - issuedAmount, 0);
  return {
    issuedAmount,
    rateizedAmount,
    paidAmount: paidAmount == null ? null : Math.abs(paidAmount),
    residualAmount: residualAmount == null ? null : Math.abs(residualAmount),
    feeAmount,
  };
}

function normalizeErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function shouldIgnorePaymentNoticesError(message: string): boolean {
  return message.includes("403") || message.includes("Module access");
}

function buildIncassTerminalMessage(job: CapacitasInCassSyncJobListItem): string {
  if (job.status === "succeeded") {
    return `Sync inCASS #${job.id} completata. Avvisi aggiornati automaticamente.`;
  }
  if (job.status === "completed_with_errors") {
    return `Sync inCASS #${job.id} completata con errori. Avvisi aggiornati automaticamente.`;
  }
  if (job.status === "cancelled") {
    return `Sync inCASS #${job.id} annullata.`;
  }
  return job.error_detail || `Sync inCASS #${job.id} fallita.`;
}

export function UtenzePaymentNoticesSection({ subjectId, token, compact = false }: Props) {
  const [notices, setNotices] = useState<AnagraficaPaymentNotice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [monitoredJobId, setMonitoredJobId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getUtenzeSubjectPaymentNotices(token, subjectId)
      .then(setNotices)
      .catch((err: unknown) => {
        const msg = normalizeErrorMessage(err);
        if (!shouldIgnorePaymentNoticesError(msg)) {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [subjectId, token]);

  useEffect(() => {
    if (monitoredJobId === null) {
      return;
    }

    let cancelled = false;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    const scheduleNextPoll = () => {
      timerId = setTimeout(() => {
        void pollJob();
      }, INCASS_JOB_POLL_MS);
    };

    const pollJob = async () => {
      try {
        const jobs = await listCapacitasInCassSyncJobs(token);
        if (cancelled) {
          return;
        }

        const job = jobs.find((item) => item.id === monitoredJobId);
        if (!job) {
          setMonitoredJobId(null);
          setError(`Job inCASS #${monitoredJobId} non trovato durante il monitoraggio.`);
          return;
        }

        if (isCapacitasInCassActiveJobStatus(job.status)) {
          setSyncMessage(`Job inCASS #${job.id} in corso. Gli avvisi saranno aggiornati automaticamente al completamento.`);
          scheduleNextPoll();
          return;
        }

        setMonitoredJobId(null);
        if (job.status === "succeeded" || job.status === "completed_with_errors") {
          const refreshed = await getUtenzeSubjectPaymentNotices(token, subjectId);
          if (cancelled) {
            return;
          }
          setNotices(refreshed);
          setError(null);
        } else {
          setError(job.error_detail || `Job inCASS #${job.id} terminato con stato ${job.status}.`);
        }
        setSyncMessage(buildIncassTerminalMessage(job));
      } catch (err: unknown) {
        if (cancelled) {
          return;
        }
        setMonitoredJobId(null);
        setError(normalizeErrorMessage(err));
      }
    };

    void pollJob();

    return () => {
      cancelled = true;
      if (timerId !== null) {
        clearTimeout(timerId);
      }
    };
  }, [monitoredJobId, subjectId, token]);

  async function handleRefreshFromInCass() {
    setSyncing(true);
    setError(null);
    setSyncMessage(null);
    try {
      const job = await createCapacitasInCassSyncJob(token, {
        subject_ids: [subjectId],
        include_details: true,
        include_partitario: true,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: 250,
      });
      setSyncMessage(`Job inCASS #${job.id} accodato. Monitoraggio automatico in corso.`);
      const refreshed = await getUtenzeSubjectPaymentNotices(token, subjectId);
      setNotices(refreshed);
      setMonitoredJobId(job.id);
    } catch (err: unknown) {
      setError(normalizeErrorMessage(err));
    } finally {
      setSyncing(false);
    }
  }

  const summary = buildPaymentNoticeSummary(notices);
  const latestSync = notices[0]?.synced_at ?? null;
  const refreshButton = (
    <button
      className="inline-flex items-center justify-center rounded-xl border border-[#1D4E35] bg-[#1D4E35] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[#173f2b] disabled:cursor-not-allowed disabled:opacity-60"
      type="button"
      onClick={() => void handleRefreshFromInCass()}
      disabled={syncing || monitoredJobId !== null}
    >
      {syncing ? "Accodo sync..." : monitoredJobId !== null ? "Sync in corso..." : "Aggiorna da inCASS"}
    </button>
  );

  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
      <div className={compact ? "border-b border-[#edf1eb] px-5 py-4" : "border-b border-[#edf1eb] p-5"}>
        {compact ? (
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">
                <FolderIcon className="h-3 w-3" />
                Avvisi
              </div>
              <h3 className="mt-3 text-lg font-semibold text-gray-900">Avvisi di pagamento</h3>
              <p className="mt-1 text-sm text-gray-500">Storico sintetico del soggetto con stato e residuo.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {refreshButton}
              <div className="rounded-2xl border border-sky-100 bg-sky-50/70 px-3 py-2 text-sm text-sky-900">
                <p className="font-semibold">{latestSync ? `Ultima sync: ${new Date(latestSync).toLocaleString("it-IT")}` : "Sync disponibile"}</p>
                <p className="mt-1 text-xs">{notices.length} avviso{notices.length !== 1 ? "i" : ""}</p>
              </div>
              <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-3 py-2 text-sm text-amber-900">
                <p className="font-semibold">Residuo totale</p>
                <p className="mt-1 text-xs">{formatMoney(String(summary.totalResiduo))}</p>
              </div>
            </div>
          </div>
        ) : (
          <ModuleWorkspaceHero
            compact
            badge={
              <>
                <FolderIcon className="h-3.5 w-3.5" />
                Avvisi
              </>
            }
            title="Avvisi di pagamento sincronizzati sul soggetto."
            description="Storico avvisi, stato sintetico, dettagli informativi e PDF recuperati da Capacitas."
            actions={
              <>
                {refreshButton}
                <ModuleWorkspaceNoticeCard
                  compact
                  title={latestSync ? `Ultima sync: ${new Date(latestSync).toLocaleString("it-IT")}` : "Sync disponibile"}
                  description={`${notices.length} avviso${notices.length !== 1 ? "i" : ""} presenti per il soggetto.`}
                  tone="info"
                />
                <ModuleWorkspaceNoticeCard compact title="Residuo totale" description={formatMoney(String(summary.totalResiduo))} tone="warning" />
                <ModuleWorkspaceNoticeCard compact title={summary.label} description={summary.description} tone={summary.status === "paid" ? "success" : "warning"} />
              </>
            }
          />
        )}
      </div>
      <div className={compact ? "space-y-4 p-4" : "space-y-4 p-5"}>
        {loading ? <p className="text-sm text-gray-500">Caricamento avvisi in corso.</p> : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {syncMessage ? (
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {syncMessage}
          </div>
        ) : null}
        <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : "md:grid-cols-3"}`}>
          <ModuleWorkspaceMiniStat eyebrow="Avvisi" value={notices.length} description="Record avviso importati dal portale pagamenti." compact />
          <ModuleWorkspaceMiniStat eyebrow="Con stato pagato" value={summary.paidCount} description="Avvisi pagati o con pagamenti registrati." tone="success" compact />
          <ModuleWorkspaceMiniStat eyebrow="Residuo €" value={formatMoney(String(summary.totalResiduo))} description="Somma dei residui presenti negli avvisi sincronizzati." compact />
        </div>
        {!loading && notices.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[#d9dfd6] bg-[#fbfcfa] px-4 py-5 text-sm text-gray-600">
            Nessun avviso inCASS sincronizzato per questo soggetto. Usa &quot;Aggiorna da inCASS&quot; per accodare il recupero dal portale Capacitas.
          </div>
        ) : null}
        <div className="space-y-3">
          {notices.map((notice) => {
            const detailFields = notice.detail_info_text ? extractNoticeDetailFields(notice.detail_info_text) : [];
            const rateDetails = notice.detail_info_text ? extractNoticeRateDetails(notice.detail_info_text) : [];
            const residualNotes = notice.detail_info_text ? buildNoticeResidualNotes(notice.detail_info_text, detailFields) : [];
            const noticePaymentStatus = getPaymentNoticeStatus(notice);
            const noticePaymentLabel = noticePaymentStatus === "paid" ? "Pagato" : noticePaymentStatus === "partial" ? "Parziale" : "Non pagato";
            const rateizationInsight = buildRateizationInsight(notice);

            return (
              <article key={notice.id} className={`rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] ${compact ? "px-4 py-3" : "px-4 py-4"}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-gray-900">Avviso {notice.source_notice_id}</p>
                      {notice.anno ? <span className="rounded-full bg-[#eef3ec] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">Anno {notice.anno}</span> : null}
                      {notice.stato_label ? <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">{notice.stato_label}</span> : null}
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${noticePaymentStatus === "paid" ? "bg-emerald-50 text-emerald-700" : noticePaymentStatus === "partial" ? "bg-amber-50 text-amber-800" : "bg-rose-50 text-rose-700"}`}>
                        {noticePaymentLabel}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-xs leading-5 text-gray-500">
                      {notice.display_name ?? "Intestatario non disponibile"}{notice.data_scadenza ? ` · scadenza ${notice.data_scadenza}` : ""}
                    </p>
                    {notice.lista_descrizione ? <p className="mt-1 truncate text-xs text-gray-400">Lista {notice.lista_id ?? "—"} · {notice.lista_descrizione}</p> : null}
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Residuo €</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatMoney(notice.importo_residuo)}</p>
                  </div>
                </div>

                <div className={`${compact ? "mt-3" : "mt-4"} grid gap-2 text-xs text-gray-600 md:grid-cols-3`}>
                  <div>Carico: <span className="font-medium text-gray-900">{formatMoney(notice.importo_carico)}</span></div>
                  <div>Riscosso: <span className="font-medium text-gray-900">{formatMoney(notice.importo_riscosso)}</span></div>
                  <div>Rateizzato: <span className="font-medium text-gray-900">{formatMoney(notice.importo_rateizzato)}</span></div>
                </div>

                {rateizationInsight ? (
                  <div className={`${compact ? "mt-3" : "mt-4"} rounded-2xl border border-amber-200 bg-amber-50/70 p-3`}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-800">Rateizzazione inCASS</p>
                        <p className="mt-1 text-xs leading-5 text-amber-900">
                          GAIA usa il totale emesso rateizzato da inCASS e il versato dell&apos;utenza per leggere il saldo.
                        </p>
                      </div>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-amber-900">
                        Costo rateizzazione {formatMoneyNumber(rateizationInsight.feeAmount)}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 text-xs md:grid-cols-4">
                      <div className="rounded-xl bg-white px-3 py-2"><span className="text-gray-500">Emesso inCASS</span><p className="mt-1 font-semibold text-gray-900">{formatMoneyNumber(rateizationInsight.issuedAmount)}</p></div>
                      <div className="rounded-xl bg-white px-3 py-2"><span className="text-gray-500">Totale rateizzato</span><p className="mt-1 font-semibold text-gray-900">{formatMoneyNumber(rateizationInsight.rateizedAmount)}</p></div>
                      <div className="rounded-xl bg-white px-3 py-2"><span className="text-gray-500">Versato utenza</span><p className="mt-1 font-semibold text-gray-900">{formatMoneyNumber(rateizationInsight.paidAmount)}</p></div>
                      <div className="rounded-xl bg-white px-3 py-2"><span className="text-gray-500">Residuo inCASS</span><p className="mt-1 font-semibold text-gray-900">{formatMoneyNumber(rateizationInsight.residualAmount)}</p></div>
                    </div>
                  </div>
                ) : null}

                <div className={`${compact ? "mt-3" : "mt-4"} flex flex-wrap items-center justify-between gap-3`}>
                  <div className="flex flex-wrap gap-2">
                    {notice.detail_url ? (
                      <Link
                        href={notice.detail_url}
                        target="_blank"
                        className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                      >
                        <DocumentIcon className="h-3.5 w-3.5" />
                        Apri dettaglio
                      </Link>
                    ) : null}
                    {notice.pdf_links.map((pdf) => (
                      <Link
                        key={`${notice.id}-${pdf.url}`}
                        href={pdf.download_url ?? pdf.url}
                        target="_blank"
                        className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                      >
                        PDF {pdf.label ?? ""}
                      </Link>
                    ))}
                  </div>
                  {notice.synced_at ? <span className="text-xs text-gray-400">Sync {new Date(notice.synced_at).toLocaleString("it-IT")}</span> : null}
                </div>

                {notice.detail_info_text ? (
                  <details className={`${compact ? "mt-3" : "mt-4"} rounded-2xl border border-gray-100 bg-gray-50/80 p-3`}>
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                      Dettagli informativi
                    </summary>
                    <div className="mt-3 space-y-3">
                      {detailFields.length ? (
                        <div className="grid gap-2 md:grid-cols-2">
                          {detailFields.map((field, index) => (
                            <div key={`${notice.id}-${field.label}-${index}`} className="rounded-2xl border border-[#e5ece6] bg-white px-3 py-2">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">{field.label}</p>
                              <p className="mt-1 text-sm leading-5 text-gray-800">{field.value}</p>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {rateDetails.length ? (
                        <div className="rounded-2xl border border-[#e5ece6] bg-white p-3">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Rate e scadenze</p>
                          <div className="mt-2 grid gap-2 md:grid-cols-3">
                            {rateDetails.map((rate, index) => (
                              <div key={`${notice.id}-${rate.label}-${rate.dueDate ?? "na"}-${index}`} className="rounded-xl border border-[#edf1eb] bg-[#f8faf7] px-3 py-2">
                                <p className="text-xs font-semibold text-gray-700">{rate.label}</p>
                                <p className="mt-1 text-xs text-gray-500">{rate.dueDate ?? "Scadenza non disponibile"}</p>
                                <p className="mt-1 text-sm font-medium text-gray-900">{rate.amount ?? "Importo non disponibile"}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {residualNotes.length ? (
                        <div className="rounded-2xl border border-[#e5ece6] bg-white p-3">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Note aggiuntive</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {residualNotes.map((note, index) => (
                              <span key={`${notice.id}-${note}-${index}`} className="rounded-full border border-[#dce6df] bg-[#f8faf7] px-3 py-1.5 text-xs text-gray-700">
                                {note}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </details>
                ) : null}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
