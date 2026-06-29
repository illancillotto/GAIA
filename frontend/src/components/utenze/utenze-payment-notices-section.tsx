"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, FolderIcon } from "@/components/ui/icons";
import { getUtenzeSubjectPaymentNotices } from "@/lib/api";
import type { AnagraficaPaymentNotice } from "@/types/api";

type Props = {
  subjectId: string;
  token: string;
  compact?: boolean;
};

type NoticeDetailField = {
  label: string;
  value: string;
};

type NoticeRateDetail = {
  label: string;
  dueDate: string | null;
  amount: string | null;
};

function parseNoticeAmount(value: string | null | undefined): number | null {
  if (!value) return null;
  const raw = String(value).trim().replace(/[^\d,.-]/g, "");
  if (!raw) return null;

  if (raw.includes(",") && raw.includes(".")) {
    const normalized = raw.replace(/\./g, "").replace(",", ".");
    const parsed = Number(normalized);
    return Number.isNaN(parsed) ? null : parsed;
  }

  if (raw.includes(",")) {
    const parsed = Number(raw.replace(",", "."));
    return Number.isNaN(parsed) ? null : parsed;
  }

  if (raw.includes(".")) {
    const parts = raw.split(".");
    if (parts.length === 2 && parts[1]?.length === 2) {
      const parsed = Number(raw);
      return Number.isNaN(parsed) ? null : parsed;
    }
    const parsed = Number(parts.join(""));
    return Number.isNaN(parsed) ? null : parsed;
  }

  const parsed = Number(raw);
  return Number.isNaN(parsed) ? null : parsed;
}

function isPaidLikeStatus(value: string | null | undefined): boolean {
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  return normalized.includes("pagato") && !normalized.startsWith("non pagato");
}

function formatMoney(value: string | null | undefined): string {
  if (!value) return "—";
  const normalized = parseNoticeAmount(value);
  if (normalized == null || Number.isNaN(normalized)) return value;
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(normalized);
}

function normalizeNoticeDetailText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function extractTokenSegment(source: string, startToken: string, endTokens: string[]): string | null {
  const startIndex = source.indexOf(startToken);
  if (startIndex === -1) return null;
  const afterStart = source.slice(startIndex + startToken.length);
  let endIndex = afterStart.length;
  for (const endToken of endTokens) {
    const candidateIndex = afterStart.indexOf(endToken);
    if (candidateIndex !== -1 && candidateIndex < endIndex) {
      endIndex = candidateIndex;
    }
  }
  const extracted = afterStart.slice(0, endIndex).trim();
  return extracted || null;
}

function extractNoticeDetailFields(detailText: string): NoticeDetailField[] {
  const normalized = normalizeNoticeDetailText(detailText);
  const fields: NoticeDetailField[] = [];
  const pushField = (label: string, value: string | null) => {
    if (!value) return;
    fields.push({ label, value: value.trim() });
  };

  pushField("Codice fiscale", extractTokenSegment(normalized, "Codice fiscale ", [" Dati anagrafici", " Partita ", " Avviso "]));
  pushField("Dati anagrafici", extractTokenSegment(normalized, "Dati anagrafici ", [" Partita ", " Avviso ", " Anno "]));
  pushField("Partita", extractTokenSegment(normalized, "Partita ", [" Avviso ", " Anno "]));
  pushField("Avviso", extractTokenSegment(normalized, "Avviso ", [" Anno ", " Totale imposta "]));
  pushField("Anno", extractTokenSegment(normalized, "Anno ", [" Totale imposta ", " Totale residuo "]));
  pushField("Totale imposta", extractTokenSegment(normalized, "Totale imposta ", [" Totale residuo ", " Totale sgravio "]));
  pushField("Totale residuo", extractTokenSegment(normalized, "Totale residuo ", [" Totale sgravio ", " Invio ", " Ultimo invio "]));
  pushField("Totale sgravio", extractTokenSegment(normalized, "Totale sgravio ", [" Invio ", " Ultimo invio ", " Ruolo "]));
  pushField("Ultimo invio", extractTokenSegment(normalized, "Ultimo invio ", [" Ruolo ", " Lista "]));
  pushField("Ruolo", extractTokenSegment(normalized, "Ruolo ", [" Lista ", " Rate ", " Rata tot. "]));
  pushField("Lista", extractTokenSegment(normalized, "Lista ", [" Rate ", " Rata tot. ", " Trib. "]));
  pushField("Tributo", extractTokenSegment(normalized, "Trib. ", [" Raggruppamento colonne"]));

  const unique = new Map<string, string>();
  for (const field of fields) {
    if (!unique.has(field.label)) unique.set(field.label, field.value);
  }
  return Array.from(unique.entries()).map(([label, value]) => ({ label, value }));
}

function extractNoticeRateDetails(detailText: string): NoticeRateDetail[] {
  const normalized = normalizeNoticeDetailText(detailText);
  const ratePattern = /(Rata tot\.|Rata \d+)\s+(\d{2}\/\d{2}\/\d{4})?\s*(€\s*[\d.,]+)?/g;
  const matches = Array.from(normalized.matchAll(ratePattern));
  const results: NoticeRateDetail[] = [];
  for (const match of matches) {
    const label = match[1]?.trim();
    if (!label) continue;
    results.push({
      label,
      dueDate: match[2]?.trim() ?? null,
      amount: match[3]?.replace(/\s+/g, " ").trim() ?? null,
    });
  }
  return results;
}

function buildNoticeResidualNotes(detailText: string, fields: NoticeDetailField[]): string[] {
  let normalized = normalizeNoticeDetailText(detailText);
  const noiseTokens = [
    /inCass(?:\s+inCass)?\s+\S+\s+\S+/i,
    /Indietro/i,
    /Azioni/i,
    /Aggiungi pag\. manuale/i,
    /Rimuovi pag\. manuale/i,
    /Annulla assegnaz\. boll\./i,
    /Aggiungi a Mailing/i,
    /List Rottamazione avviso/i,
    /Sgravio Inserisci/i,
    /Rimuovi Immagine pag\. Inserisci/i,
    /Rimuovi Modifica Tipo di avviso/i,
    /Blocca Aggiorna dettagli/i,
    /Rateizzazione/i,
    /AVVISO NON RISCOSSO/i,
    /Codice consorzio:\s*\d+/i,
    /Server:\s*[^ ]+/i,
    /Base dati:\s*[^ ]+/i,
    /Chiudi/i,
    /Manuale/i,
    /Tile bloccate/i,
    /Mappa del sito/i,
    /principale ricerca avvisi dettaglio Dettaglio/i,
    /Raggruppamento colonne/i,
    /©\s*\d{4}(?:-\d{4})?\s*Capacitas/i,
    /Contattaci/i,
    /Privacy/i,
    /Informativa Cookies/i,
  ];

  for (const pattern of noiseTokens) {
    normalized = normalized.replace(pattern, " ");
  }
  for (const field of fields) {
    normalized = normalized.replace(field.label, " ");
    normalized = normalized.replace(field.value, " ");
  }
  normalized = normalized.replace(/(Rata tot\.|Rata \d+)\s+\d{2}\/\d{2}\/\d{4}\s*€\s*[\d.,]+/g, " ");
  normalized = normalized.replace(/\s+/g, " ").trim();
  if (!normalized) return [];

  return normalized
    .split(/(?<=\.)\s+|\s{2,}/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 6);
}

export function UtenzePaymentNoticesSection({ subjectId, token, compact = false }: Props) {
  const [notices, setNotices] = useState<AnagraficaPaymentNotice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUtenzeSubjectPaymentNotices(token, subjectId)
      .then(setNotices)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (!msg.includes("403") && !msg.includes("Module access")) {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [subjectId, token]);

  if (loading || error || notices.length === 0) return null;

  const totalResiduo = notices.reduce((sum, notice) => sum + (parseNoticeAmount(notice.importo_residuo) ?? 0), 0);
  const paidCount = notices.filter((notice) => isPaidLikeStatus(notice.stato_label)).length;
  const latestSync = notices[0]?.synced_at ?? null;

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
              <div className="rounded-2xl border border-sky-100 bg-sky-50/70 px-3 py-2 text-sm text-sky-900">
                <p className="font-semibold">{latestSync ? `Ultima sync: ${new Date(latestSync).toLocaleString("it-IT")}` : "Sync disponibile"}</p>
                <p className="mt-1 text-xs">{notices.length} avviso{notices.length !== 1 ? "i" : ""}</p>
              </div>
              <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-3 py-2 text-sm text-amber-900">
                <p className="font-semibold">Residuo totale</p>
                <p className="mt-1 text-xs">{formatMoney(String(totalResiduo))}</p>
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
                <ModuleWorkspaceNoticeCard
                  compact
                  title={latestSync ? `Ultima sync: ${new Date(latestSync).toLocaleString("it-IT")}` : "Sync disponibile"}
                  description={`${notices.length} avviso${notices.length !== 1 ? "i" : ""} presenti per il soggetto.`}
                  tone="info"
                />
                <ModuleWorkspaceNoticeCard compact title="Residuo totale" description={formatMoney(String(totalResiduo))} tone="warning" />
              </>
            }
          />
        )}
      </div>
      <div className={compact ? "space-y-4 p-4" : "space-y-4 p-5"}>
        <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : "md:grid-cols-3"}`}>
          <ModuleWorkspaceMiniStat eyebrow="Avvisi" value={notices.length} description="Record avviso importati dal portale pagamenti." compact />
          <ModuleWorkspaceMiniStat eyebrow="Con stato pagato" value={paidCount} description="Avvisi pagati o con pagamenti registrati." tone="success" compact />
          <ModuleWorkspaceMiniStat eyebrow="Residuo €" value={formatMoney(String(totalResiduo))} description="Somma dei residui presenti negli avvisi sincronizzati." compact />
        </div>
        <div className="space-y-3">
          {notices.map((notice) => {
            const detailFields = notice.detail_info_text ? extractNoticeDetailFields(notice.detail_info_text) : [];
            const rateDetails = notice.detail_info_text ? extractNoticeRateDetails(notice.detail_info_text) : [];
            const residualNotes = notice.detail_info_text ? buildNoticeResidualNotes(notice.detail_info_text, detailFields) : [];

            return (
              <article key={notice.id} className={`rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] ${compact ? "px-4 py-3" : "px-4 py-4"}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-gray-900">Avviso {notice.source_notice_id}</p>
                      {notice.anno ? <span className="rounded-full bg-[#eef3ec] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">Anno {notice.anno}</span> : null}
                      {notice.stato_label ? <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">{notice.stato_label}</span> : null}
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
                        href={pdf.url}
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
