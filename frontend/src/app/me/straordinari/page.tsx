"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import { downloadMeStraordinariRequest, previewMeStraordinariRequest } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { MeStraordinariPreviewResponse } from "@/types/api";

type DraftItem = {
  recordId: string;
  workDate: string;
  startTime: string | null;
  endTime: string | null;
  durationMinutes: number;
  durationLabel: string;
  originalDurationMinutes: number;
  pauseDeductionMinutes: number;
  lunchBreakMinutes: number | null;
  durationAdjustmentReason: string | null;
  selected: boolean;
  motivation: string;
};

type PauseFilter = "all" | "adjusted" | "plain";

function formatMonthLabel(value: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat("it-IT", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function formatDurationLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function buildFilename(preview: MeStraordinariPreviewResponse | null, format: "xlsx" | "pdf"): string {
  /* v8 ignore next -- defensive fallback; download buttons are only enabled after preview load. */
  if (!preview) return `richiesta-straordinari.${format}`;
  const month = preview.period_start.slice(0, 7);
  return `richiesta-straordinari-${month}.${format}`;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function MeStraordinariPage() {
  const [preview, setPreview] = useState<MeStraordinariPreviewResponse | null>(null);
  const [draftItems, setDraftItems] = useState<DraftItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState<"xlsx" | "pdf" | null>(null);
  const [pauseFilter, setPauseFilter] = useState<PauseFilter>("all");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function loadPreview() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile. Effettua il login.");
        setIsLoading(false);
        return;
      }
      try {
        const result = await previewMeStraordinariRequest(token);
        setPreview(result);
        setDraftItems(
          result.items.map((item) => ({
            recordId: item.record_id,
            workDate: item.work_date,
            startTime: item.start_time,
            endTime: item.end_time,
            durationMinutes: item.duration_minutes,
            durationLabel: item.duration_label,
            originalDurationMinutes: item.original_duration_minutes ?? item.duration_minutes,
            pauseDeductionMinutes: item.pause_deduction_minutes ?? 0,
            lunchBreakMinutes: item.lunch_break_minutes ?? null,
            durationAdjustmentReason: item.duration_adjustment_reason ?? null,
            selected: true,
            motivation: item.motivation,
          })),
        );
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento richiesta straordinari");
      } finally {
        setIsLoading(false);
      }
    }

    void loadPreview();
  }, []);

  const selectedItems = useMemo(() => draftItems.filter((item) => item.selected), [draftItems]);
  const adjustedItemsCount = useMemo(() => draftItems.filter((item) => item.pauseDeductionMinutes > 0).length, [draftItems]);
  const alignedItemsCount = useMemo(() => draftItems.filter((item) => item.pauseDeductionMinutes === 0 && item.originalDurationMinutes !== item.durationMinutes).length, [draftItems]);
  const visibleDraftItems = useMemo(
    () =>
      draftItems.filter((item) => {
        if (pauseFilter === "adjusted") return item.pauseDeductionMinutes > 0;
        if (pauseFilter === "plain") return item.pauseDeductionMinutes === 0 && item.originalDurationMinutes === item.durationMinutes;
        return true;
      }),
    [draftItems, pauseFilter],
  );
  const selectedMinutesLabel = useMemo(() => {
    if (!preview) return "00:00";
    const total = selectedItems.reduce((sum, item) => sum + item.durationMinutes, 0);
    return formatDurationLabel(total);
  }, [preview, selectedItems]);

  async function handleDownload(format: "xlsx" | "pdf") {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Effettua il login.");
      return;
    }
    /* v8 ignore next 4 -- defensive guard; action buttons are disabled with no selected rows. */
    if (selectedItems.length === 0) {
      setError("Seleziona almeno una giornata da includere nel modulo.");
      return;
    }

    setIsDownloading(format);
    setError(null);
    setSuccess(null);
    try {
      const blob = await downloadMeStraordinariRequest(token, format, {
        items: selectedItems.map((item) => ({
          record_id: item.recordId,
          motivation: item.motivation,
        })),
      });
      downloadBlob(blob, buildFilename(preview, format));
      setSuccess(format === "pdf" ? "PDF generato. Se la conversione non e disponibile usa il file Excel." : "Excel generato: puoi stamparlo o inoltrarlo al caposettore.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore generazione modulo straordinari");
    } finally {
      setIsDownloading(null);
    }
  }

  return (
    <ProtectedPage
      title="Richiesta straordinari"
      description="Compila le motivazioni, genera il modulo e invialo al tuo caposettore."
      breadcrumb="La mia attività"
      requiredModule="presenze"
    >
      <section className="page-body space-y-6">
        <article className="rounded-[28px] border border-emerald-100 bg-gradient-to-br from-[#F3FAF0] via-white to-[#FFF7E8] p-6 shadow-sm">
          <p className="section-kicker">Self-service operatore</p>
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-emerald-950">Modulo richiesta straordinari</h2>
              <p className="mt-2 max-w-3xl text-sm text-gray-600">
                Il modulo usa il template ufficiale <span className="font-semibold">Straordinari.xlsx</span>. Le giornate candidate arrivano dal mese precedente e
                puoi correggere le motivazioni prima di scaricare il file.
              </p>
            </div>
            <div className="rounded-2xl border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Totale selezionato</p>
              <p className="mt-1 text-2xl font-semibold text-emerald-950">{selectedMinutesLabel}</p>
            </div>
          </div>
        </article>

        {error ? <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p> : null}
        {success ? <p className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">{success}</p> : null}

        <article className="rounded-[24px] border border-gray-100 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="section-kicker">Periodo modulo</p>
              <h3 className="mt-1 text-xl font-semibold text-gray-900">
                {preview ? formatMonthLabel(preview.period_start) : "Caricamento"}
              </h3>
              {preview ? (
                <p className="mt-1 text-sm text-gray-500">
                  {preview.collaborator.name} · matricola {preview.collaborator.employee_code}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" onClick={() => void handleDownload("xlsx")} disabled={isLoading || isDownloading != null || selectedItems.length === 0}>
                {isDownloading === "xlsx" ? "Genero Excel..." : "Scarica Excel"}
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleDownload("pdf")} disabled={isLoading || isDownloading != null || selectedItems.length === 0}>
                {isDownloading === "pdf" ? "Genero PDF..." : "Scarica PDF"}
              </button>
            </div>
          </div>

          {isLoading ? (
            <p className="mt-6 text-sm text-gray-500">Caricamento giornate con straordinario...</p>
          ) : draftItems.length === 0 ? (
            <div className="mt-6">
              <EmptyState icon={DocumentIcon} title="Nessuno straordinario nel mese precedente" description="Non risultano giornate candidate per compilare il modulo." />
            </div>
          ) : (
            <>
              <div className="mt-5 rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
                <span className="font-semibold">Filtro pausa:</span> le giornate con entrata al mattino e uscita pomeridiana/serale senza pausa da almeno 30 minuti vengono rettificate
                automaticamente. Pausa detratta: {adjustedItemsCount}. Allineate alla fascia post-pausa: {alignedItemsCount}.
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  ["all", "Tutte"],
                  ["adjusted", "Solo pausa detratta"],
                  ["plain", "Senza rettifica"],
                ].map(([value, label]) => (
                  <button key={value} className={pauseFilter === value ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setPauseFilter(value as PauseFilter)}>
                    {label}
                  </button>
                ))}
              </div>

              {visibleDraftItems.length === 0 ? (
                <div className="mt-6">
                  <EmptyState icon={DocumentIcon} title="Nessuna riga per questo filtro" description="Cambia filtro per rivedere le altre giornate candidate." />
                </div>
              ) : (
                <div className="mt-6 overflow-hidden rounded-2xl border border-gray-100">
                  <div className="grid grid-cols-[44px_150px_110px_1fr] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-gray-400">
                    <span />
                    <span>Data</span>
                    <span>Ore</span>
                    <span>Motivazione</span>
                  </div>
                  {visibleDraftItems.map((item) => (
                    <div key={item.recordId} className="grid grid-cols-[44px_150px_110px_1fr] gap-3 border-b border-gray-100 px-4 py-3 last:border-b-0">
                      <input
                        aria-label={`Includi ${formatDateLabel(item.workDate)}`}
                        checked={item.selected}
                        className="mt-2 h-4 w-4"
                        type="checkbox"
                        onChange={(event) =>
                          setDraftItems((current) =>
                            current.map((candidate) => (candidate.recordId === item.recordId ? { ...candidate, selected: event.target.checked } : candidate)),
                          )
                        }
                      />
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{formatDateLabel(item.workDate)}</p>
                        <p className="mt-1 text-xs text-gray-500">
                          {item.startTime && item.endTime ? `${item.startTime}-${item.endTime}` : "Orario da verificare"}
                        </p>
                      </div>
                      <div className="pt-2">
                        <p className="text-sm font-semibold text-emerald-800">{item.durationLabel}</p>
                        {item.pauseDeductionMinutes > 0 ? (
                          <p className="mt-1 text-xs font-medium text-amber-700">
                            Da {formatDurationLabel(item.originalDurationMinutes)}, pausa -{formatDurationLabel(item.pauseDeductionMinutes)}
                          </p>
                        ) : null}
                        {item.pauseDeductionMinutes === 0 && item.originalDurationMinutes !== item.durationMinutes ? (
                          <p className="mt-1 text-xs font-medium text-sky-700">
                            Da {formatDurationLabel(item.originalDurationMinutes)} a {item.durationLabel}
                          </p>
                        ) : null}
                        {item.lunchBreakMinutes !== null && item.pauseDeductionMinutes === 0 ? (
                          <p className="mt-1 text-xs text-gray-500">Pausa rilevata: {formatDurationLabel(item.lunchBreakMinutes)}</p>
                        ) : null}
                      </div>
                      <div>
                        {item.durationAdjustmentReason ? <p className="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">{item.durationAdjustmentReason}</p> : null}
                        <textarea
                          aria-label={`Motivazione ${formatDateLabel(item.workDate)}`}
                          className="form-control min-h-[74px]"
                          value={item.motivation}
                          placeholder="Es. intervento urgente, reperibilità, chiusura servizio..."
                          onChange={(event) =>
                            setDraftItems((current) =>
                              current.map((candidate) => (candidate.recordId === item.recordId ? { ...candidate, motivation: event.target.value } : candidate)),
                            )
                          }
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </article>
      </section>
    </ProtectedPage>
  );
}
