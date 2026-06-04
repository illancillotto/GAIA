"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { listRuoloParticelle } from "@/lib/ruolo-api";
import type { RuoloParticellaResponse } from "@/types/ruolo";

const PAGE_SIZE = 50;

function formatHa(value: number | null): string {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(value)} ha`;
}

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function MatchBadge({ item }: { item: RuoloParticellaResponse }) {
  if (item.cat_particella_id) {
    return (
      <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-800">
        Collegata
      </span>
    );
  }
  if (item.ade_scan_classification === "suppressed") {
    return (
      <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-800">
        Soppressa AdE
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-rose-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-rose-800">
      Non collegata
    </span>
  );
}

function RuoloParticellePageFallback() {
  return (
    <RuoloModulePage
      title="Particelle a Ruolo"
      description="Vista storica delle particelle del ruolo consortile."
      breadcrumb="Ruolo / Particelle"
      requiredSection="ruolo.avvisi"
    >
      <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">Caricamento...</div>
    </RuoloModulePage>
  );
}

export default function RuoloParticellePage() {
  return (
    <Suspense fallback={<RuoloParticellePageFallback />}>
      <RuoloParticellePageContent />
    </Suspense>
  );
}

function RuoloParticellePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string | null>(null);
  const [items, setItems] = useState<RuoloParticellaResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedParticella, setSelectedParticella] = useState<RuoloParticellaResponse | null>(null);

  const comune = searchParams.get("comune")?.trim() || "";
  const foglio = searchParams.get("foglio")?.trim() || "";
  const particella = searchParams.get("particella")?.trim() || "";
  const anno = searchParams.get("anno")?.trim() || "";
  const matchStatus = searchParams.get("match_status")?.trim() || "";
  const matchReason = searchParams.get("match_reason")?.trim() || "";
  const unmatchedOnly = searchParams.get("unmatched_only") !== "false";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  const [filterComune, setFilterComune] = useState(comune);
  const [filterFoglio, setFilterFoglio] = useState(foglio);
  const [filterParticella, setFilterParticella] = useState(particella);
  const [filterAnno, setFilterAnno] = useState(anno);
  const [filterMatchStatus, setFilterMatchStatus] = useState(matchStatus);
  const [filterMatchReason, setFilterMatchReason] = useState(matchReason);
  const [filterUnmatchedOnly, setFilterUnmatchedOnly] = useState(unmatchedOnly);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    setFilterComune(comune);
    setFilterFoglio(foglio);
    setFilterParticella(particella);
    setFilterAnno(anno);
    setFilterMatchStatus(matchStatus);
    setFilterMatchReason(matchReason);
    setFilterUnmatchedOnly(unmatchedOnly);
  }, [anno, comune, foglio, particella, matchReason, matchStatus, unmatchedOnly]);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    listRuoloParticelle(token, {
      comune: comune || undefined,
      foglio: foglio || undefined,
      particella: particella || undefined,
      anno: anno ? Number(anno) : undefined,
      match_status: matchStatus || undefined,
      match_reason: matchReason || undefined,
      unmatched_only: unmatchedOnly,
      page,
      page_size: PAGE_SIZE,
    })
      .then(setItems)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore caricamento particelle"))
      .finally(() => setLoading(false));
  }, [anno, comune, foglio, matchReason, matchStatus, page, particella, token, unmatchedOnly]);

  function applyFilters(): void {
    const qs = new URLSearchParams();
    if (filterComune.trim()) qs.set("comune", filterComune.trim());
    if (filterFoglio.trim()) qs.set("foglio", filterFoglio.trim());
    if (filterParticella.trim()) qs.set("particella", filterParticella.trim());
    if (filterAnno.trim()) qs.set("anno", filterAnno.trim());
    if (filterMatchStatus.trim()) qs.set("match_status", filterMatchStatus.trim());
    if (filterMatchReason.trim()) qs.set("match_reason", filterMatchReason.trim());
    if (!filterUnmatchedOnly) qs.set("unmatched_only", "false");
    qs.set("page", "1");
    router.push(`/ruolo/particelle?${qs.toString()}`);
  }

  const linkedCount = useMemo(() => items.filter((item) => item.cat_particella_id).length, [items]);
  const unmatchedCount = items.length - linkedCount;
  const suppressedCount = useMemo(
    () => items.filter((item) => item.ade_scan_classification === "suppressed").length,
    [items],
  );
  const pageTotal = useMemo(() => items.reduce((sum, item) => sum + (item.importo_manut ?? 0) + (item.importo_irrig ?? 0) + (item.importo_ist ?? 0), 0), [items]);

  return (
    <RuoloModulePage
      title="Particelle a Ruolo"
      description="Vista storica delle particelle del ruolo consortile, incluse quelle non collegate al Catasto corrente."
      breadcrumb="Ruolo / Particelle"
      requiredSection="ruolo.avvisi"
    >
      <div className="space-y-8">
        {selectedParticella ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
            <div className="w-full max-w-4xl rounded-2xl bg-white shadow-2xl">
              <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="section-title">Dettaglio particella ruolo</p>
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {selectedParticella.comune_nome ?? "Comune non disponibile"} · Fg.{selectedParticella.foglio} Part.{selectedParticella.particella}
                    {selectedParticella.subalterno ? ` Sub.${selectedParticella.subalterno}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {selectedParticella.cat_particella_id ? (
                    <Link className="btn-secondary" href={`/catasto/particelle/${selectedParticella.cat_particella_id}`} target="_blank">
                      Apri Catasto
                    </Link>
                  ) : null}
                  <button className="btn-secondary" type="button" onClick={() => setSelectedParticella(null)}>
                    Chiudi
                  </button>
                </div>
              </div>
              <div className="grid gap-6 px-6 py-5 md:grid-cols-2">
                <div className="space-y-4">
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Riferimento</p>
                    <p className="mt-2 text-lg font-semibold text-gray-900">
                      {selectedParticella.comune_nome ?? "—"} · Fg.{selectedParticella.foglio} Part.{selectedParticella.particella}
                      {selectedParticella.subalterno ? ` Sub.${selectedParticella.subalterno}` : ""}
                    </p>
                    <p className="mt-2 text-sm text-gray-600">Anno tributario {selectedParticella.anno_tributario} · Distretto {selectedParticella.distretto ?? "—"}</p>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Superfici</p>
                    <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <dt className="text-gray-500">Catastale</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatHa(selectedParticella.sup_catastale_ha)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Irrigata</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatHa(selectedParticella.sup_irrigata_ha)}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Importi</p>
                    <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <dt className="text-gray-500">Manutenzione</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatEuro(selectedParticella.importo_manut)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Irrigazione</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatEuro(selectedParticella.importo_irrig)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Istituzionale</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatEuro(selectedParticella.importo_ist)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Totale</dt>
                        <dd className="mt-1 font-semibold text-gray-900">{formatEuro((selectedParticella.importo_manut ?? 0) + (selectedParticella.importo_irrig ?? 0) + (selectedParticella.importo_ist ?? 0))}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Stato collegamento</p>
                    <div className="mt-3">
                      <MatchBadge item={selectedParticella} />
                    </div>
                    <dl className="mt-3 space-y-2 text-sm text-gray-700">
                      <div className="flex justify-between gap-4">
                        <dt className="text-gray-500">Match status</dt>
                        <dd className="font-medium text-gray-900">{selectedParticella.cat_particella_match_status ?? "—"}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-gray-500">Match reason</dt>
                        <dd className="font-medium text-gray-900">{selectedParticella.cat_particella_match_reason ?? "—"}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-gray-500">Confidenza</dt>
                        <dd className="font-medium text-gray-900">{selectedParticella.cat_particella_match_confidence ?? "—"}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Scansione AdE</p>
                    <dl className="mt-3 space-y-2 text-sm text-gray-700">
                      <div className="flex justify-between gap-4">
                        <dt className="text-gray-500">Status</dt>
                        <dd className="font-medium text-gray-900">{selectedParticella.ade_scan_status ?? "—"}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-gray-500">Classificazione</dt>
                        <dd className="font-medium text-gray-900">{selectedParticella.ade_scan_classification ?? "—"}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Riferimenti tecnici</p>
                    <dl className="mt-3 space-y-2 break-all text-sm text-gray-700">
                      <div>
                        <dt className="text-gray-500">ruolo_particella_id</dt>
                        <dd className="mt-1 font-medium text-gray-900">{selectedParticella.id}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">catasto_parcel_id</dt>
                        <dd className="mt-1 font-medium text-gray-900">{selectedParticella.catasto_parcel_id ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">cat_particella_id</dt>
                        <dd className="mt-1 font-medium text-gray-900">{selectedParticella.cat_particella_id ?? "—"}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Particelle ruolo storico
            </>
          }
          title="Consulta le particelle importate dal ruolo anche quando non esistono nel Catasto corrente."
          description="Questa vista legge `ruolo_particelle`: puoi quindi trovare particelle storiche, non collegate o classificate come soppresse da AdE anche se non compaiono in `catasto/particelle`."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={filterUnmatchedOnly ? "Filtro non collegate attivo" : "Tutte le particelle ruolo"}
                description={filterUnmatchedOnly ? "La lista e limitata alle righe senza collegamento a `cat_particelle`." : "La lista include sia righe collegate sia non collegate."}
                tone={filterUnmatchedOnly ? "warning" : "info"}
              />
              <ModuleWorkspaceNoticeCard
                title={suppressedCount > 0 ? "Soppressioni AdE presenti" : "Nessuna soppressione in pagina"}
                description={suppressedCount > 0 ? `${suppressedCount} righe della pagina corrente risultano classificate come soppresse da AdE.` : "Nella pagina corrente non risultano classificazioni AdE di soppressione."}
                tone={suppressedCount > 0 ? "warning" : "success"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Righe pagina" value={items.length} hint={`Max ${PAGE_SIZE} per pagina`} />
            <ModuleWorkspaceKpiTile label="Collegate" value={linkedCount} hint="Con `cat_particella_id`" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Non collegate" value={unmatchedCount} hint="Storiche o da riallineare" variant={unmatchedCount > 0 ? "amber" : "default"} />
            <ModuleWorkspaceKpiTile label="Importi pagina" value={formatEuro(pageTotal)} hint="Somma manut.+irr.+ist." />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri</p>
            <p className="section-copy">La ricerca e applicata direttamente al dataset storico `ruolo_particelle`.</p>
          </div>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              applyFilters();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Comune</span>
                <input
                  className="form-control"
                  placeholder="Es. Mogoro"
                  value={filterComune}
                  onChange={(event) => setFilterComune(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Foglio</span>
                <input
                  className="form-control"
                  placeholder="Es. 19"
                  value={filterFoglio}
                  onChange={(event) => setFilterFoglio(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Particella</span>
                <input
                  className="form-control"
                  placeholder="Es. 1101"
                  value={filterParticella}
                  onChange={(event) => setFilterParticella(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Anno tributario</span>
                <input
                  className="form-control"
                  inputMode="numeric"
                  placeholder="Es. 2025"
                  value={filterAnno}
                  onChange={(event) => setFilterAnno(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Match status</span>
                <input
                  className="form-control"
                  placeholder="Es. unmatched"
                  value={filterMatchStatus}
                  onChange={(event) => setFilterMatchStatus(event.target.value)}
                />
              </label>
              <label className="block md:col-span-2 xl:col-span-2">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Match reason</span>
                <input
                  className="form-control"
                  placeholder="Es. no_cat_particella_match"
                  value={filterMatchReason}
                  onChange={(event) => setFilterMatchReason(event.target.value)}
                />
              </label>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={filterUnmatchedOnly}
                onChange={(event) => setFilterUnmatchedOnly(event.target.checked)}
                className="rounded border-gray-300"
              />
              Mostra solo particelle non collegate al Catasto corrente
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-primary" type="submit">Applica filtri</button>
              <button
                className="btn-secondary"
                type="button"
                onClick={() => {
                  setFilterComune("");
                  setFilterFoglio("");
                  setFilterParticella("");
                  setFilterAnno("");
                  setFilterMatchStatus("");
                  setFilterMatchReason("");
                  setFilterUnmatchedOnly(true);
                  router.push("/ruolo/particelle");
                }}
              >
                Reset
              </button>
            </div>
          </form>
        </article>

        <article className="panel-card overflow-hidden">
          {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
          {loading ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento...</div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={SearchIcon}
              title="Nessuna particella ruolo"
              description="Nessuna riga del ruolo storico corrisponde ai filtri correnti."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Stato</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Comune</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Riferimento</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Anno</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Sup. irrigata</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Importi</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Diagnostica</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {items.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer align-top transition hover:bg-[#f7fbf8]"
                    onClick={() => setSelectedParticella(item)}
                  >
                      <td className="px-4 py-4">
                        <div className="space-y-2">
                          <MatchBadge item={item} />
                          {item.ade_scan_status ? <p className="text-xs text-gray-500">AdE: {item.ade_scan_status}</p> : null}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <p className="text-sm font-medium text-gray-900">{item.comune_nome ?? "—"}</p>
                        <p className="text-xs text-gray-500">{item.comune_codice ?? "Codice comune non disponibile"}</p>
                      </td>
                      <td className="px-4 py-4">
                        <p className="text-sm text-gray-900">
                          Fg.{item.foglio} Part.{item.particella}
                          {item.subalterno ? ` Sub.${item.subalterno}` : ""}
                        </p>
                        <p className="text-xs text-gray-500">Distretto {item.distretto ?? "—"}</p>
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-700">{item.anno_tributario}</td>
                      <td className="px-4 py-4 text-sm text-gray-700">{formatHa(item.sup_irrigata_ha)}</td>
                      <td className="px-4 py-4">
                        <p className="text-sm text-gray-900">{formatEuro((item.importo_manut ?? 0) + (item.importo_irrig ?? 0) + (item.importo_ist ?? 0))}</p>
                        <p className="text-xs text-gray-500">
                          M {formatEuro(item.importo_manut)} · I {formatEuro(item.importo_irrig)} · Ist {formatEuro(item.importo_ist)}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <div className="space-y-1 text-xs text-gray-600">
                          <p>Match: {item.cat_particella_match_status ?? "—"}</p>
                          <p>Reason: {item.cat_particella_match_reason ?? "—"}</p>
                          <p>AdE class.: {item.ade_scan_classification ?? "—"}</p>
                          <p>Catasto corrente: {item.cat_particella_id ? "presente" : "assente"}</p>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>
    </RuoloModulePage>
  );
}
