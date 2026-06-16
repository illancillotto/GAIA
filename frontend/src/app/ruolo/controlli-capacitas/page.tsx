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
  getRuoloCapacitasCheckStatusDescription,
  getRuoloCapacitasCheckVerificationHint,
  getRuoloCapacitasComuneExplanation,
  getRuoloCapacitasPositionLine,
  RuoloCapacitasAmountStack,
  RuoloCapacitasDetailList,
} from "@/components/ruolo/capacitas-check-details";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { RuoloWorkspaceModal } from "@/components/ruolo/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { CalendarIcon, DocumentIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { searchUtenzeSubjects } from "@/lib/api";
import {
  buildRuoloCapacitasCheckExportUrl,
  formatRuoloCapacitasCheckStatus,
  getRuoloCapacitasCheckStatusBadgeClassName,
  getRuoloCapacitasCheck,
  getRuoloCapacitasCheckComuni,
  getRuoloStats,
  listAvvisi,
} from "@/lib/ruolo-api";
import type {
  RuoloCapacitasCheckComuneResponse,
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

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setWorkspaceModal({ href, title, description });
  }

  async function openRelevantAvvisoModal(taxCode: string): Promise<void> {
    if (!token || selectedAnno == null) return;
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
      title="Controlli Capacitas"
      description="Verifica comparativa tra ruolo importato e valori Capacitas."
      breadcrumb="Controlli Capacitas"
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
            <ModuleWorkspaceKpiTile label="Delta totale" value={formatEuro(check?.summary.delta_totale_confrontabile ?? null)} hint="Base confrontabile 0648 + 0985" />
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
                  <ModuleWorkspaceMiniStat eyebrow="Posizioni Capacitas" value={check ? formatInteger(check.summary.capacitas_positions) : "—"} description={check ? `${formatInteger(check.summary.capacitas_positions_missing_tax_code)} senza chiave fiscale utile.` : "—"} compact />
                  <ModuleWorkspaceMiniStat eyebrow="Solo ruolo" value={check ? formatInteger(check.summary.only_in_ruolo) : "—"} description="Presenti nel ruolo ma non nel dataset Capacitas dell'anno." tone={(check?.summary.only_in_ruolo ?? 0) > 0 ? "warning" : "success"} compact />
                  <ModuleWorkspaceMiniStat eyebrow="Solo Capacitas" value={check ? formatInteger(check.summary.only_in_capacitas) : "—"} description="Presenti in Capacitas ma non agganciati al ruolo." tone={(check?.summary.only_in_capacitas ?? 0) > 0 ? "warning" : "success"} compact />
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <p className="section-title">Base confrontabile</p>
                <p className="section-copy">Il delta totale usa solo 0648 e 0985. Il 0668 viene escluso dal match Capacitas.</p>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat eyebrow="Ruolo confrontabile" value={formatEuro(check?.summary.ruolo_totale_confrontabile ?? null)} description="Somma 0648 + 0985 lato ruolo." compact />
                  <ModuleWorkspaceMiniStat eyebrow="Capacitas confrontabile" value={formatEuro(check?.summary.capacitas_totale_confrontabile ?? null)} description="Somma 0648 + 0985 lato Capacitas." compact />
                  <ModuleWorkspaceMiniStat eyebrow="Match fiscali" value={check ? formatInteger(check.summary.matched_positions) : "—"} description="Chiavi presenti in entrambi i dataset." tone="success" compact />
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

            <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
              <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <SearchIcon className="h-3.5 w-3.5" />
                  Mismatch per CF/P.IVA
                </p>
                <p className="mt-3 text-lg font-semibold text-gray-900">Posizioni da verificare sul dettaglio avvisi.</p>
              </div>
              <div className="overflow-x-auto p-6">
                {check && check.items.length > 0 ? (
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Posizione</th>
                        <th className="px-4 py-3">Stato</th>
                        <th className="px-4 py-3">Valori ruolo</th>
                        <th className="px-4 py-3">Valori Capacitas</th>
                        <th className="px-4 py-3">Delta</th>
                        <th className="px-4 py-3">Verifica</th>
                        <th className="px-4 py-3">Azioni</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {check.items.map((item) => (
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
                            <RuoloCapacitasAmountStack
                              amount0648={item.ruolo_0648}
                              amount0985={item.ruolo_0985}
                              total={item.ruolo_totale_confrontabile}
                              tone="ruolo"
                            />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <RuoloCapacitasAmountStack
                              amount0648={item.capacitas_0648}
                              amount0985={item.capacitas_0985}
                              total={item.capacitas_totale_confrontabile}
                              tone="capacitas"
                            />
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
                            <p className="text-sm text-gray-700">{getRuoloCapacitasCheckVerificationHint(item.status)}</p>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="flex flex-col items-start gap-2">
                              <button
                                type="button"
                                onClick={() => void openRelevantAvvisoModal(item.tax_code)}
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
                  <EmptyState icon={DocumentIcon} title="Nessun mismatch rilevato" description="Per l'anno selezionato non risultano scostamenti oltre soglia sul confronto per chiave fiscale." />
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
                        <th className="px-4 py-3">Valori Capacitas</th>
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
                            <RuoloCapacitasAmountStack amount0648={item.capacitas_0648} amount0985={item.capacitas_0985} total={item.capacitas_totale_confrontabile} tone="capacitas" />
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
    </RuoloModulePage>
  );
}
