"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import {
  formatRuoloCapacitasDiagnosis,
  getRuoloCapacitasDiagnosisBadgeClassName,
  getRuoloCapacitasDiagnosisDescription,
  getRuoloCapacitasEvaluationSummary,
  getRuoloCapacitasEvidenceLines,
  getRuoloCapacitasCheckStatusDescription,
  getRuoloCapacitasCheckVerificationHint,
  getRuoloCapacitasComuneExplanation,
  getRuoloCapacitasPositionLine,
  RuoloCapacitasAmountStack,
  RuoloCapacitasDetailList,
} from "@/components/ruolo/capacitas-check-details";
import { RuoloCapacitasCalculationModal } from "@/components/ruolo/capacitas-calculation-modal";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { RuoloWorkspaceModal } from "@/components/ruolo/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { CalendarIcon, DocumentIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { getUtenzeSubjectPaymentNotices, searchUtenzeSubjects } from "@/lib/api";
import {
  buildRuoloCapacitasCheckExportUrl,
  formatRuoloCapacitasCheckStatus,
  getRuoloCapacitasCalculationDetail,
  getRuoloCapacitasCheckStatusBadgeClassName,
  getRuoloCapacitasCheck,
  getRuoloCapacitasCheckComuni,
  getRuoloStats,
  listAvvisi,
} from "@/lib/ruolo-api";
import type {
  RuoloCapacitasDiagnosis,
  RuoloCapacitasCalculationDetailResponse,
  RuoloCapacitasCheckComuneResponse,
  RuoloCapacitasCheckItemResponse,
  RuoloCapacitasCheckResponse,
  RuoloStatsByAnnoResponse,
} from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

export default function RuoloCapacitasChecksPage() {
  const [token, setToken] = useState<string | null>(null);
  const [stats, setStats] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [selectedAnno, setSelectedAnno] = useState<number | null>(null);
  const [check, setCheck] = useState<RuoloCapacitasCheckResponse | null>(null);
  const [checkComuni, setCheckComuni] = useState<RuoloCapacitasCheckComuneResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingCheck, setLoadingCheck] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subjectLookupBusyTaxCode, setSubjectLookupBusyTaxCode] = useState<string | null>(null);
  const [avvisoLookupBusyTaxCode, setAvvisoLookupBusyTaxCode] = useState<string | null>(null);
  const [workspaceModal, setWorkspaceModal] = useState<{ href: string; title: string; description?: string | null } | null>(null);
  const [missingRuoloModal, setMissingRuoloModal] = useState<{ taxCode: string; displayName?: string | null } | null>(null);
  const [calculationItem, setCalculationItem] = useState<RuoloCapacitasCheckItemResponse | null>(null);
  const [calculationDetail, setCalculationDetail] = useState<RuoloCapacitasCalculationDetailResponse | null>(null);
  const [calculationLoading, setCalculationLoading] = useState(false);
  const [calculationError, setCalculationError] = useState<string | null>(null);
  const [onlyAnomalyDrivenCases, setOnlyAnomalyDrivenCases] = useState(false);
  const [diagnosisFilter, setDiagnosisFilter] = useState<"all" | RuoloCapacitasDiagnosis>("all");

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    getRuoloStats(token)
      .then((statsData) => {
        setStats(statsData.items);
        setSelectedAnno((current) => current ?? statsData.items[0]?.anno_tributario ?? null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore caricamento annualita"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!token || selectedAnno == null) return;
    setLoadingCheck(true);
    setError(null);
    Promise.all([
      getRuoloCapacitasCheck(token, selectedAnno, 0.01, 50),
      getRuoloCapacitasCheckComuni(token, selectedAnno, 20),
    ])
      .then(([checkData, comuniData]) => {
        setCheck(checkData);
        setCheckComuni(comuniData);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore controllo Capacitas"))
      .finally(() => setLoadingCheck(false));
  }, [token, selectedAnno]);

  const availableYears = useMemo(
    () => [...stats].sort((left, right) => right.anno_tributario - left.anno_tributario),
    [stats],
  );
  const exportUrl = selectedAnno != null ? buildRuoloCapacitasCheckExportUrl(selectedAnno, 0.01) : null;
  const filteredCheckItems = useMemo(
    () =>
      (check?.items ?? []).filter(
        (item) =>
          (!onlyAnomalyDrivenCases || item.anomaly_driven_case)
          && (diagnosisFilter === "all" || item.diagnosis === diagnosisFilter),
      ),
    [check, onlyAnomalyDrivenCases, diagnosisFilter],
  );

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setWorkspaceModal({ href, title, description });
  }

  async function openCalculationModal(item: RuoloCapacitasCheckItemResponse): Promise<void> {
    if (!token || selectedAnno == null) return;
    setCalculationItem(item);
    setCalculationDetail(null);
    setCalculationError(null);
    setCalculationLoading(true);
    try {
      const detail = await getRuoloCapacitasCalculationDetail(token, selectedAnno, item.tax_code);
      setCalculationDetail(detail);
    } catch (detailError) {
      setCalculationError(detailError instanceof Error ? detailError.message : "Errore caricamento dettaglio calcolo");
    } finally {
      setCalculationLoading(false);
    }
  }

  function openCapacitasStoricoModal(taxCode?: string | null, displayName?: string | null): void {
    openWorkspaceModal(
      "/elaborazioni/capacitas?section=storico",
      "Anagrafica Capacitas",
      taxCode
        ? `Apri il workspace Capacitas Storico anagrafico per verificare ${displayName || taxCode}.`
        : "Apri il workspace Capacitas Storico anagrafico.",
    );
  }

  async function openCapacitasRoleLink(taxCode: string, displayName?: string | null): Promise<void> {
    if (!token) return;
    setError(null);
    try {
      const response = await searchUtenzeSubjects(token, taxCode, 20);
      const normalized = taxCode.trim().toUpperCase().replace(/\s+/g, "");
      const exactMatches = response.items.filter((item) => {
        const itemCf = item.codice_fiscale?.trim().toUpperCase().replace(/\s+/g, "") ?? "";
        const itemPiva = item.partita_iva?.trim().toUpperCase().replace(/\s+/g, "") ?? "";
        return itemCf === normalized || itemPiva === normalized;
      });

      if (exactMatches.length !== 1) {
        setError(`Impossibile risolvere un soggetto GAIA univoco per ${displayName || taxCode}.`);
        return;
      }

      const notices = await getUtenzeSubjectPaymentNotices(token, exactMatches[0].id);
      const year = selectedAnno != null ? String(selectedAnno) : null;
      const yearNotice = notices.find((notice) => notice.anno === year && notice.detail_url);
      const fallbackNotice = notices.find((notice) => notice.detail_url);
      const detailUrl = yearNotice?.detail_url ?? fallbackNotice?.detail_url ?? null;

      if (!detailUrl) {
        setError(`Nessun link ruolo Capacitas disponibile per ${displayName || taxCode}.`);
        return;
      }

      window.open(detailUrl, "_blank", "noopener,noreferrer");
    } catch (lookupError) {
      setError(lookupError instanceof Error ? lookupError.message : "Errore apertura ruolo Capacitas");
    }
  }

  async function openRelevantAvvisoModal(
    taxCode: string,
    options?: { ruoloMissing?: boolean; displayName?: string | null },
  ): Promise<void> {
    if (!token || selectedAnno == null) return;
    if (options?.ruoloMissing) {
      setMissingRuoloModal({ taxCode, displayName: options.displayName });
      return;
    }
    setAvvisoLookupBusyTaxCode(taxCode);
    setError(null);
    try {
      const response = await listAvvisi(token, {
        anno: selectedAnno,
        codice_fiscale: taxCode,
        page: 1,
        page_size: 10,
      });

      if (response.items.length === 0) {
        setError(`Nessun avviso trovato per ${taxCode} nell'annualita ${selectedAnno}.`);
        return;
      }

      if (response.items.length === 1) {
        const avviso = response.items[0];
        openWorkspaceModal(
          `/ruolo/avvisi/${avviso.id}`,
          "Dettaglio avviso",
          `Avviso ${avviso.codice_cnc} dell'annualita ${selectedAnno} per ${taxCode}.`,
        );
        return;
      }

      openWorkspaceModal(
        `/ruolo/avvisi?anno=${selectedAnno}&codice_fiscale=${encodeURIComponent(taxCode)}&focus=mismatch`,
        "Avvisi collegati allo scostamento",
        `Trovati ${response.items.length} avvisi per ${taxCode} nell'annualita ${selectedAnno}: seleziona quello corretto.`,
      );
    } catch (lookupError) {
      setError(lookupError instanceof Error ? lookupError.message : "Errore apertura avviso");
    } finally {
      setAvvisoLookupBusyTaxCode(null);
    }
  }

  async function openSubjectDetailModal(taxCode: string, displayName?: string | null): Promise<void> {
    if (!token) return;
    setSubjectLookupBusyTaxCode(taxCode);
    setError(null);
    try {
      const response = await searchUtenzeSubjects(token, taxCode, 20);
      const normalized = taxCode.trim().toUpperCase().replace(/\s+/g, "");
      const exactMatches = response.items.filter((item) => {
        const itemCf = item.codice_fiscale?.trim().toUpperCase().replace(/\s+/g, "") ?? "";
        const itemPiva = item.partita_iva?.trim().toUpperCase().replace(/\s+/g, "") ?? "";
        return itemCf === normalized || itemPiva === normalized;
      });

      if (exactMatches.length === 1) {
        const match = exactMatches[0];
        openWorkspaceModal(
          `/utenze/${match.id}`,
          "Dettaglio soggetto",
          `Scheda GAIA per ${match.display_name || displayName || taxCode}.`,
        );
        return;
      }

      if (exactMatches.length > 1) {
        setError(`Trovati piu soggetti GAIA per ${taxCode}. Apri gli avvisi e verifica l'anagrafica manualmente.`);
        return;
      }

      setError(`Nessun soggetto GAIA trovato per ${taxCode}.`);
    } catch (lookupError) {
      setError(lookupError instanceof Error ? lookupError.message : "Errore ricerca soggetto");
    } finally {
      setSubjectLookupBusyTaxCode(null);
    }
  }

  return (
    <RuoloModulePage
      title="Audit Capacitas"
      description="Vista tecnica di audit tra ruolo importato, ricalcolo GAIA e snapshot Capacitas."
      breadcrumb="Audit Capacitas"
      requiredSection="ruolo.dashboard"
      topbarActions={
        token && exportUrl ? (
          <a
            href={`${exportUrl}&token=${token}`}
            className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
            download={`ruolo_capacitas_check_${selectedAnno}.csv`}
          >
            Esporta CSV
          </a>
        ) : undefined
      }
    >
      <div className="space-y-8">
        {missingRuoloModal ? (
          <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
            <div className="w-full max-w-2xl rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
              <div className="border-b border-gray-100 px-6 py-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Ruolo assente</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-900">Nessun avviso ruolo in GAIA</h2>
                <p className="mt-2 text-sm text-gray-500">
                  Per {missingRuoloModal.displayName || missingRuoloModal.taxCode} non risulta alcun avviso ruolo nell&apos;annualita selezionata. Puoi continuare la verifica dal lato Capacitas o dalla scheda soggetto.
                </p>
              </div>
              <div className="space-y-4 px-6 py-5 text-sm text-gray-700">
                <div className="rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">CF/P.IVA</p>
                  <p className="mt-1 font-medium text-gray-900">{missingRuoloModal.taxCode}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setMissingRuoloModal(null);
                      void openCapacitasRoleLink(missingRuoloModal.taxCode, missingRuoloModal.displayName);
                    }}
                    className="rounded-lg border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Apri ruolo Capacitas
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMissingRuoloModal(null);
                      openCapacitasStoricoModal(missingRuoloModal.taxCode, missingRuoloModal.displayName);
                    }}
                    className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800 transition hover:bg-sky-100"
                  >
                    Apri anagrafica Capacitas
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMissingRuoloModal(null);
                      void openSubjectDetailModal(missingRuoloModal.taxCode, missingRuoloModal.displayName);
                    }}
                    className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-800 transition hover:bg-violet-100"
                  >
                    Apri soggetto GAIA
                  </button>
                </div>
              </div>
              <div className="flex justify-end border-t border-gray-100 px-6 py-4">
                <button className="btn-secondary" type="button" onClick={() => setMissingRuoloModal(null)}>
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        ) : null}
        <RuoloWorkspaceModal
          description={workspaceModal?.description}
          href={workspaceModal?.href ?? null}
          onClose={() => setWorkspaceModal(null)}
          open={workspaceModal != null}
          title={workspaceModal?.title ?? "Workspace"}
        />
        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Supervisione economica
            </>
          }
          title="Console di controllo ruolo vs Capacitas."
          description="Analizza scostamenti economici tra ruolo e Capacitas per annualita, individua anomalie per CF/P.IVA o comune ed entra direttamente nella lista avvisi da verificare."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={selectedAnno != null ? `Annualita in analisi: ${selectedAnno}` : "Nessuna annualita disponibile"}
                description={selectedAnno != null ? "Il confronto usa i tributi comuni 0648 e 0985. Il 0668 resta solo informativo lato ruolo." : "Importa almeno un anno ruolo per attivare il controllo."}
                tone={selectedAnno != null ? "info" : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={check ? `${formatInteger(check.summary.mismatch_positions)} posizioni da verificare` : "Controllo in caricamento"}
                description={check ? `Match fiscali: ${formatInteger(check.summary.matched_positions)}. Solo ruolo: ${formatInteger(check.summary.only_in_ruolo)}. Solo Capacitas: ${formatInteger(check.summary.only_in_capacitas)}.` : "La console carichera automaticamente riepilogo, mismatch ed export."}
                tone={check && check.summary.mismatch_positions > 0 ? "warning" : "success"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Delta totale" value={formatEuro(check?.summary.delta_totale_confrontabile ?? null)} hint="Ruolo meno GAIA su base 0648 + 0985" />
            <ModuleWorkspaceKpiTile label="Delta GAIA/Excel" value={formatEuro(check?.summary.delta_gaia_excel_totale_confrontabile ?? null)} hint="Ricalcolo GAIA meno snapshot Excel" variant={(check?.summary.delta_gaia_excel_totale_confrontabile ?? 0) !== 0 ? "amber" : "default"} />
            <ModuleWorkspaceKpiTile label="Delta 0648" value={formatEuro(check?.summary.delta_totale_0648 ?? null)} hint="Ruolo meno Capacitas" variant={(check?.summary.delta_totale_0648 ?? 0) !== 0 ? "amber" : "default"} />
            <ModuleWorkspaceKpiTile label="Delta 0985" value={formatEuro(check?.summary.delta_totale_0985 ?? null)} hint="Ruolo meno Capacitas" variant={(check?.summary.delta_totale_0985 ?? 0) !== 0 ? "amber" : "default"} />
            <ModuleWorkspaceKpiTile label="0668 ruolo" value={formatEuro(check?.summary.ruolo_totale_0668 ?? null)} hint="Dato informativo non confrontato" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
          <div className="flex flex-wrap items-end gap-4">
            <label className="min-w-[220px]">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Anno tributario</span>
              <select
                value={selectedAnno ?? ""}
                onChange={(event) => setSelectedAnno(event.target.value ? Number(event.target.value) : null)}
                className="w-full rounded-xl border border-[#d8dfd3] bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {availableYears.map((item) => (
                  <option key={item.anno_tributario} value={item.anno_tributario}>
                    {item.anno_tributario}
                  </option>
                ))}
              </select>
            </label>
            <div className="text-sm text-gray-500">
              <p className="font-medium text-gray-900">Posizioni considerate</p>
              <p>Aggregazione per codice fiscale / partita IVA normalizzati e per comune.</p>
            </div>
          </div>
        </section>

        {loading || loadingCheck ? (
          <p className="text-sm text-gray-400">Caricamento controlli Capacitas...</p>
        ) : error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : selectedAnno == null ? (
          <EmptyState icon={CalendarIcon} title="Nessuna annualita disponibile" description="Importa il primo ruolo per abilitare la console di controllo Capacitas." />
        ) : (
          <>
            <section className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Riepilogo mismatch anagrafici</p>
                <p className="section-copy">Le posizioni senza chiave fiscale o presenti in un solo dataset richiedono bonifica o verifica import.</p>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat eyebrow="Posizioni ruolo" value={check ? formatInteger(check.summary.ruolo_positions) : "—"} description={check ? `${formatInteger(check.summary.ruolo_positions_missing_tax_code)} senza chiave fiscale utile.` : "—"} compact />
                  <ModuleWorkspaceMiniStat eyebrow="Posizioni batch attivo" value={check ? formatInteger(check.summary.capacitas_positions) : "—"} description={check ? `${formatInteger(check.summary.capacitas_positions_missing_tax_code)} senza chiave fiscale utile.` : "—"} compact />
                  <ModuleWorkspaceMiniStat eyebrow="Solo ruolo" value={check ? formatInteger(check.summary.only_in_ruolo) : "—"} description="Presenti nel ruolo ma non nel batch Capacitas attivo dell'anno." tone={(check?.summary.only_in_ruolo ?? 0) > 0 ? "warning" : "success"} compact />
                  <ModuleWorkspaceMiniStat eyebrow="Solo batch attivo" value={check ? formatInteger(check.summary.only_in_capacitas) : "—"} description="Presenti nel batch Capacitas attivo ma non agganciati al ruolo." tone={(check?.summary.only_in_capacitas ?? 0) > 0 ? "warning" : "success"} compact />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <ModuleWorkspaceMiniStat eyebrow="Priorita ruolo" value={check ? formatInteger(check.summary.diagnosis_ruolo_count) : "—"} description="Primo controllo su ruolo/InCass." compact />
                  <ModuleWorkspaceMiniStat eyebrow="Priorita GAIA" value={check ? formatInteger(check.summary.diagnosis_gaia_count) : "—"} description="Primo controllo su ricalcolo GAIA." compact />
                  <ModuleWorkspaceMiniStat eyebrow="Priorita Excel" value={check ? formatInteger(check.summary.diagnosis_excel_count) : "—"} description="Primo controllo su snapshot Excel." compact />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <ModuleWorkspaceMiniStat
                    eyebrow="Casi guidati da anomalie"
                    value={formatInteger((check?.items ?? []).filter((item) => item.anomaly_driven_case).length)}
                    description="Scostamenti GAIA quasi interamente spiegati da righe anomale."
                    tone={(check?.items ?? []).some((item) => item.anomaly_driven_case) ? "warning" : "default"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Casi visibili"
                    value={formatInteger(filteredCheckItems.length)}
                    description={onlyAnomalyDrivenCases ? "Filtro attivo: mostriamo solo i casi guidati da anomalie." : "Vista completa dei mismatch per CF/P.IVA."}
                    compact
                  />
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Base confrontabile</p>
                <p className="section-copy">Il delta totale usa solo 0648 e 0985. Il 0668 viene escluso dal match Capacitas.</p>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat eyebrow="Ruolo confrontabile" value={formatEuro(check?.summary.ruolo_totale_confrontabile ?? null)} description="Somma 0648 + 0985 lato ruolo." compact />
                  <ModuleWorkspaceMiniStat eyebrow="GAIA confrontabile" value={formatEuro(check?.summary.gaia_totale_confrontabile ?? null)} description="Somma 0648 + 0985 ricalcolata da GAIA sul batch attivo." compact />
                  <ModuleWorkspaceMiniStat eyebrow="Match fiscali" value={check ? formatInteger(check.summary.matched_positions) : "—"} description="Chiavi presenti in entrambi i dataset." tone="success" compact />
                </div>
                <div className="mt-4 rounded-2xl border border-[#dbe7f4] bg-[#f7fbff] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-800">Snapshot Excel importato</p>
                  <p className="mt-2 text-sm text-gray-600">
                    Totale confrontabile importato: {formatEuro(check?.summary.excel_totale_confrontabile ?? null)}. Delta GAIA/Excel: {formatEuro(check?.summary.delta_gaia_excel_totale_confrontabile ?? null)}. Questo valore resta visibile come riferimento diagnostico e non determina il delta principale.
                  </p>
                </div>
              </article>
            </section>

            <section className="grid gap-4 xl:grid-cols-3">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Che cosa confrontiamo</p>
                <p className="section-copy">Il controllo usa solo `0648` e `0985`. Il `0668` resta visibile a cruscotto ma non entra nel match economico con Capacitas.</p>
              </article>
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Chiave del match</p>
                <p className="section-copy">Ogni riga e aggregata per `codice fiscale / partita IVA` normalizzati. Le posizioni senza identificativo fiscale utile non possono essere confrontate automaticamente.</p>
              </article>
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Azioni disponibili</p>
                <p className="section-copy">`Apri avviso` prova ad aprire direttamente il dettaglio del ruolo per il soggetto e l&apos;anno selezionati. Se nello stesso anno esistono piu avvisi, apre la lista filtrata. `Apri soggetto` mostra direttamente la scheda GAIA quando il CF/P.IVA trova un match univoco.</p>
              </article>
            </section>

            <section className="grid gap-4 xl:grid-cols-3">
              <article className="rounded-[28px] border border-amber-200 bg-[#fffaf4] p-6 shadow-panel">
                <p className="section-title">Come valutare Priorita ruolo</p>
                <p className="section-copy">Se GAIA ed Excel sono coerenti, il caso va letto prima sul ruolo: avviso, partitario, pubblicazione o raccolta InCass.</p>
              </article>
              <article className="rounded-[28px] border border-sky-200 bg-[#f7fbff] p-6 shadow-panel">
                <p className="section-title">Come valutare Priorita GAIA</p>
                <p className="section-copy">Se il ruolo e piu vicino all&apos;Excel che al ricalcolo, il caso merita controllo su imponibile, ettari, coltura, aliquote e anomalie di riga.</p>
              </article>
              <article className="rounded-[28px] border border-fuchsia-200 bg-[#fff7fc] p-6 shadow-panel">
                <p className="section-title">Come valutare Priorita Excel</p>
                <p className="section-copy">Se ruolo e GAIA convergono ma lo snapshot no, conviene rivalutare import Excel, batch attivo e storico acquisito.</p>
              </article>
            </section>

            <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
              <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <SearchIcon className="h-3.5 w-3.5" />
                  Mismatch per CF/P.IVA
                </p>
                <p className="mt-3 text-lg font-semibold text-gray-900">Posizioni da verificare sul dettaglio avvisi.</p>
              </div>
              <div className="overflow-x-auto p-6">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-gray-500">
                    {onlyAnomalyDrivenCases
                      ? `Mostriamo ${formatInteger(filteredCheckItems.length)} casi in cui almeno il 95% del gap GAIA/Excel è spiegato da righe anomale.`
                      : `Mostriamo ${formatInteger(filteredCheckItems.length)} mismatch per chiave fiscale.`}
                    {diagnosisFilter !== "all" ? ` Diagnosi attiva: ${formatRuoloCapacitasDiagnosis(diagnosisFilter)}.` : ""}
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                      <input
                        type="checkbox"
                        checked={onlyAnomalyDrivenCases}
                        onChange={(event) => setOnlyAnomalyDrivenCases(event.target.checked)}
                        className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-500"
                      />
                      Solo guidati da anomalie
                    </label>
                    <label className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-900">
                      <span>Diagnosi</span>
                      <select
                        value={diagnosisFilter}
                        onChange={(event) => setDiagnosisFilter(event.target.value as "all" | RuoloCapacitasDiagnosis)}
                        className="rounded-lg border border-sky-200 bg-white px-2 py-1 text-sm text-sky-900 outline-none focus:border-sky-500"
                      >
                        <option value="all">Tutte</option>
                        <option value="problema_ruolo">Priorita ruolo</option>
                        <option value="problema_ricalcolo_gaia">Priorita GAIA</option>
                        <option value="problema_snapshot_excel">Priorita Excel</option>
                      </select>
                    </label>
                  </div>
                </div>
                {filteredCheckItems.length > 0 ? (
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                        <tr>
                          <th className="px-4 py-3">Posizione</th>
                          <th className="px-4 py-3">Stato</th>
                          <th className="px-4 py-3">Diagnosi</th>
                          <th className="px-4 py-3">Segnale GAIA</th>
                          <th className="px-4 py-3">Valori ruolo</th>
                        <th className="px-4 py-3">Valori GAIA</th>
                        <th className="px-4 py-3">Excel importato</th>
                        <th className="px-4 py-3">Delta</th>
                        <th className="px-4 py-3">Valutazione</th>
                        <th className="px-4 py-3">Azioni</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {filteredCheckItems.map((item) => (
                        <tr key={item.tax_code}>
                          <td className="px-4 py-3 align-top">
                            <p className="font-medium text-gray-900">{item.ruolo_display_name ?? item.capacitas_display_name ?? item.tax_code}</p>
                            <p className="text-xs text-gray-500">{item.tax_code}</p>
                            <RuoloCapacitasDetailList>
                              <p>{getRuoloCapacitasPositionLine(item)}</p>
                            </RuoloCapacitasDetailList>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getRuoloCapacitasCheckStatusBadgeClassName(item.status)}`}>
                              {formatRuoloCapacitasCheckStatus(item.status)}
                            </span>
                            <RuoloCapacitasDetailList>
                              <p>{getRuoloCapacitasCheckStatusDescription(item.status)}</p>
                            </RuoloCapacitasDetailList>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getRuoloCapacitasDiagnosisBadgeClassName(item.diagnosis)}`}>
                              {formatRuoloCapacitasDiagnosis(item.diagnosis)}
                            </span>
                            <RuoloCapacitasDetailList>
                              <p>{getRuoloCapacitasDiagnosisDescription(item.diagnosis)}</p>
                            </RuoloCapacitasDetailList>
                          </td>
                          <td className="px-4 py-3 align-top">
                            {item.anomaly_driven_case ? (
                              <div className="space-y-2">
                                <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">
                                  Guidato da anomalie
                                </span>
                                <RuoloCapacitasDetailList>
                                  <p>{item.anomalous_rows_count} righe anomale spiegano il {item.anomaly_gap_share.toLocaleString("it-IT", { maximumFractionDigits: 1 })}% del gap GAIA/Excel.</p>
                                </RuoloCapacitasDetailList>
                              </div>
                            ) : (
                              <RuoloCapacitasDetailList>
                                <p>{item.anomalous_rows_count > 0 ? `${item.anomalous_rows_count} righe anomale, copertura gap ${item.anomaly_gap_share.toLocaleString("it-IT", { maximumFractionDigits: 1 })}%.` : "Nessun segnale anomalo prevalente."}</p>
                              </RuoloCapacitasDetailList>
                            )}
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack
                              amount0648={item.ruolo_0648}
                              amount0985={item.ruolo_0985}
                              total={item.ruolo_totale_confrontabile}
                              tone="ruolo"
                            />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack
                              amount0648={item.gaia_0648}
                              amount0985={item.gaia_0985}
                              total={item.gaia_totale_confrontabile}
                              tone="capacitas"
                            />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="space-y-2">
                              <RuoloCapacitasAmountStack
                                amount0648={item.excel_0648}
                                amount0985={item.excel_0985}
                                total={item.excel_totale_confrontabile}
                                tone="neutral"
                              />
                              <p className="text-xs text-gray-500">
                                Delta GAIA/Excel: <span className="font-semibold text-gray-700">{formatEuro(item.delta_gaia_excel_totale_confrontabile)}</span>
                              </p>
                              <button
                                type="button"
                                onClick={() => void openCapacitasRoleLink(item.tax_code, item.capacitas_display_name ?? item.ruolo_display_name)}
                                className="rounded-lg border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-800 transition hover:bg-sky-100"
                              >
                                Apri ruolo Capacitas
                              </button>
                            </div>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack
                              amount0648={item.delta_0648}
                              amount0985={item.delta_0985}
                              total={item.delta_totale_confrontabile}
                              tone="delta"
                            />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="space-y-2">
                              <p className="text-sm font-medium text-gray-900">{getRuoloCapacitasEvaluationSummary(item)}</p>
                              <RuoloCapacitasDetailList>
                                {getRuoloCapacitasEvidenceLines(item).map((line) => (
                                  <p key={line}>{line}</p>
                                ))}
                                <p>{getRuoloCapacitasCheckVerificationHint(item.status)}</p>
                              </RuoloCapacitasDetailList>
                            </div>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="flex flex-col items-start gap-2">
                              <button
                                type="button"
                                onClick={() => void openCalculationModal(item)}
                                className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-900 transition hover:bg-amber-100"
                              >
                                Apri calcolo
                              </button>
                              <button
                                type="button"
                                onClick={() => void openRelevantAvvisoModal(item.tax_code, {
                                  ruoloMissing: item.status === "only_in_capacitas",
                                  displayName: item.capacitas_display_name ?? item.ruolo_display_name,
                                })}
                                disabled={avvisoLookupBusyTaxCode === item.tax_code}
                                className="rounded-lg border border-[#d6e5db] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                              >
                                {avvisoLookupBusyTaxCode === item.tax_code ? "Apertura avviso..." : "Apri avviso"}
                              </button>
                              <button
                                type="button"
                                onClick={() => void openSubjectDetailModal(
                                  item.tax_code,
                                  item.ruolo_display_name ?? item.capacitas_display_name,
                                )}
                                disabled={subjectLookupBusyTaxCode === item.tax_code}
                                className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-800 transition hover:bg-sky-100 disabled:cursor-wait disabled:opacity-70"
                              >
                                {subjectLookupBusyTaxCode === item.tax_code ? "Apertura soggetto..." : "Apri soggetto"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <EmptyState
                    icon={DocumentIcon}
                    title={onlyAnomalyDrivenCases ? "Nessun caso guidato da anomalie" : "Nessun mismatch rilevato"}
                    description={onlyAnomalyDrivenCases
                      ? "Disattiva il filtro per tornare alla vista completa dei mismatch."
                      : "Per l'anno selezionato non risultano scostamenti oltre soglia sul confronto per chiave fiscale."}
                  />
                )}
              </div>
            </section>

            <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
              <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <CalendarIcon className="h-3.5 w-3.5" />
                  Breakdown per comune
                </p>
                <p className="mt-3 text-lg font-semibold text-gray-900">Scostamenti aggregati territorio per territorio.</p>
              </div>
              <div className="overflow-x-auto p-6">
                {checkComuni && checkComuni.items.length > 0 ? (
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Comune</th>
                        <th className="px-4 py-3">Valori ruolo</th>
                        <th className="px-4 py-3">Valori GAIA</th>
                        <th className="px-4 py-3">Excel importato</th>
                        <th className="px-4 py-3">Delta</th>
                        <th className="px-4 py-3">Come leggerlo</th>
                        <th className="px-4 py-3">Azioni</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {checkComuni.items.map((item) => (
                        <tr key={item.comune_nome}>
                          <td className="px-4 py-3 align-top">
                            <p className="font-medium text-gray-900">{item.comune_nome}</p>
                            <RuoloCapacitasDetailList>
                              <p>Aggregato territoriale su tutte le posizioni del comune per l&apos;anno selezionato.</p>
                            </RuoloCapacitasDetailList>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack amount0648={item.ruolo_0648} amount0985={item.ruolo_0985} total={item.ruolo_totale_confrontabile} tone="ruolo" />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack amount0648={item.gaia_0648} amount0985={item.gaia_0985} total={item.gaia_totale_confrontabile} tone="capacitas" />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="space-y-2">
                              <RuoloCapacitasAmountStack amount0648={item.excel_0648} amount0985={item.excel_0985} total={item.excel_totale_confrontabile} tone="neutral" />
                              <p className="text-xs text-gray-500">
                                Delta GAIA/Excel: <span className="font-semibold text-gray-700">{formatEuro(item.delta_gaia_excel_totale_confrontabile)}</span>
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack amount0648={item.delta_0648} amount0985={item.delta_0985} total={item.delta_totale_confrontabile} tone="delta" />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <p className="text-sm text-gray-700">{getRuoloCapacitasComuneExplanation(item)}</p>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              onClick={() => openWorkspaceModal(
                                `/ruolo/avvisi?anno=${selectedAnno}&comune=${encodeURIComponent(item.comune_nome)}&focus=mismatch`,
                                "Avvisi del comune in verifica",
                                `Lista avvisi filtrata per il comune ${item.comune_nome} nell'annualita ${selectedAnno}.`,
                              )}
                              className="rounded-lg border border-[#d6e5db] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                            >
                              Apri avvisi
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <EmptyState icon={CalendarIcon} title="Nessun confronto per comune" description="Non ci sono righe sufficienti per costruire il breakdown territoriale dell'anno selezionato." />
                )}
              </div>
            </section>
          </>
        )}
      </div>

      <RuoloCapacitasCalculationModal
        open={calculationItem != null}
        item={calculationItem}
        detail={calculationDetail}
        loading={calculationLoading}
        error={calculationError}
        onClose={() => {
          setCalculationItem(null);
          setCalculationDetail(null);
          setCalculationError(null);
          setCalculationLoading(false);
        }}
      />
    </RuoloModulePage>
  );
}
