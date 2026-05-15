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
import { DocumentIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { buildExportCsvUrl, listAvvisi } from "@/lib/ruolo-api";
import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

const PAGE_SIZE = 25;

export default function RuoloAvvisiPage() {
  return (
    <Suspense fallback={<RuoloAvvisiPageFallback />}>
      <RuoloAvvisiPageContent />
    </Suspense>
  );
}

function RuoloAvvisiPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string | null>(null);
  const [avvisi, setAvvisi] = useState<RuoloAvvisoListItemResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAvviso, setSelectedAvviso] = useState<RuoloAvvisoListItemResponse | null>(null);

  const query = searchParams.get("q")?.trim() || "";
  const unlinked = searchParams.get("unlinked") === "true";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  const [filterQuery, setFilterQuery] = useState(query);
  const [filterUnlinked, setFilterUnlinked] = useState(unlinked);

  useEffect(() => {
    setFilterQuery(query);
  }, [query]);

  useEffect(() => {
    setFilterUnlinked(unlinked);
  }, [unlinked]);

  useEffect(() => {
    const normalizedQuery = filterQuery.trim();
    const currentQuery = query.trim();

    if (normalizedQuery.length > 0 && normalizedQuery.length < 3) {
      return;
    }
    if (normalizedQuery === currentQuery && filterUnlinked === unlinked) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      const qs = new URLSearchParams();
      if (normalizedQuery) qs.set("q", normalizedQuery);
      if (filterUnlinked) qs.set("unlinked", "true");
      qs.set("page", "1");
      router.replace(`/ruolo/avvisi?${qs}`);
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [filterQuery, filterUnlinked, query, router, unlinked]);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    listAvvisi(token, {
      q: query || undefined,
      unlinked,
      page,
      page_size: PAGE_SIZE,
    })
      .then((r) => {
        setAvvisi(r.items);
        setTotal(r.total);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore"))
      .finally(() => setLoading(false));
  }, [token, query, unlinked, page]);

  function setPage(nextPage: number) {
    const qs = new URLSearchParams(searchParams.toString());
    qs.set("page", String(nextPage));
    router.push(`/ruolo/avvisi?${qs}`);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const exportUrl = buildExportCsvUrl({ q: query || undefined, unlinked });

  const linkedCount = useMemo(() => avvisi.filter((item) => item.is_linked).length, [avvisi]);
  const orphanCount = avvisi.length - linkedCount;
  const pageTotal = useMemo(
    () => avvisi.reduce((sum, item) => sum + (item.importo_totale_euro ?? 0), 0),
    [avvisi],
  );

  return (
    <RuoloModulePage
      title="Avvisi Ruolo"
      description="Elenco degli avvisi consortili importati dal Ruolo."
      breadcrumb="Avvisi"
      requiredSection="ruolo.avvisi"
      topbarActions={
        token ? (
          <a
            href={`${exportUrl}&token=${token}`}
            className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
            download="avvisi_ruolo.csv"
          >
            Esporta CSV
          </a>
        ) : undefined
      }
    >
      <div className="space-y-8">
        {selectedAvviso ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
            <div className="flex h-full max-h-[94vh] w-full max-w-6xl flex-col rounded-2xl bg-white shadow-2xl">
              <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="section-title">Dettaglio avviso</p>
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {selectedAvviso.display_name ?? selectedAvviso.nominativo_raw ?? selectedAvviso.codice_cnc}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Link className="btn-secondary" href={`/ruolo/avvisi/${selectedAvviso.id}`} target="_blank">
                    Apri pagina
                  </Link>
                  <button className="btn-secondary" type="button" onClick={() => setSelectedAvviso(null)}>
                    Chiudi
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden p-4">
                <iframe
                  key={selectedAvviso.id}
                  src={`/ruolo/avvisi/${selectedAvviso.id}?embedded=1`}
                  title={`Dettaglio avviso ${selectedAvviso.codice_cnc}`}
                  className="h-full w-full rounded-xl border border-gray-200 bg-white"
                />
              </div>
            </div>
          </div>
        ) : null}

        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Consultazione avvisi
            </>
          }
          title="Ricerca, filtra e apri gli avvisi del ruolo consortile."
          description="Ricerca rapida, indicatori di collegamento anagrafico e accesso al dettaglio avviso senza uscire dal cruscotto."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={loading ? "Caricamento dataset" : `${total} avvisi nel risultato`}
                description={
                  query
                    ? `Ricerca attiva su "${query}".`
                    : "Nessun filtro testuale attivo: stai consultando l'intero storico disponibile."
                }
                tone={loading ? "warning" : "info"}
              />
              <ModuleWorkspaceNoticeCard
                title={orphanCount > 0 ? "Orfani presenti nella pagina" : "Pagina allineata"}
                description={
                  orphanCount > 0
                    ? `${orphanCount} avvisi della pagina corrente non risultano collegati a un soggetto GAIA.`
                    : "Gli avvisi caricati nella pagina corrente risultano già collegati oppure non ci sono risultati."
                }
                tone={orphanCount > 0 ? "warning" : "success"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile
              label="Risultati totali"
              value={total}
              hint={`Pagina ${page}${totalPages > 0 ? ` di ${totalPages}` : ""}`}
            />
            <ModuleWorkspaceKpiTile
              label="Collegati pagina"
              value={linkedCount}
              hint="Soggetti già mappati"
              variant="emerald"
            />
            <ModuleWorkspaceKpiTile
              label="Orfani pagina"
              value={orphanCount}
              hint="Da verificare in anagrafica"
              variant={orphanCount > 0 ? "amber" : "default"}
            />
            <ModuleWorkspaceKpiTile
              label="Totale pagina"
              value={formatEuro(pageTotal)}
              hint="Somma degli importi visibili"
            />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <section className="grid gap-4">
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Ricerca avvisi</p>
              <p className="section-copy">
                Inserisci almeno 3 lettere o un riferimento utile come CF, comune, anno, codice utenza o CNC.
              </p>
            </div>
            <div className="space-y-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                <label className="block flex-1">
                  <span className="sr-only">Cerca avviso</span>
                  <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                    <SearchIcon className="h-5 w-5 text-gray-400" />
                    <input
                      type="search"
                      placeholder="Es. Rossi, RSSMRA80A01H501Z, Oristano, 2025, U12345, CNC-001"
                      value={filterQuery}
                      onChange={(e) => setFilterQuery(e.target.value)}
                      className="w-full border-0 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
                    />
                  </div>
                </label>
                <label className="flex items-center gap-3 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-700 xl:shrink-0">
                  <input
                    type="checkbox"
                    checked={filterUnlinked}
                    onChange={(e) => setFilterUnlinked(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Solo avvisi non collegati
                </label>
              </div>
              {filterQuery.trim().length === 0 ? (
                <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <p className="text-sm font-medium text-gray-900">Ricerca pronta</p>
                  <p className="mt-1 text-sm text-gray-500">Digita le prime 3 lettere per vedere i soggetti corrispondenti.</p>
                </div>
              ) : null}
              {filterQuery.trim().length > 0 && filterQuery.trim().length < 3 ? (
                <p className="text-sm text-gray-500">Inserisci almeno 3 caratteri per avviare la ricerca.</p>
              ) : null}
                <div className="flex flex-wrap items-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setFilterQuery("");
                      setFilterUnlinked(false);
                      router.push("/ruolo/avvisi?page=1");
                    }}
                    className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2.5 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Reset
                  </button>
                </div>
            </div>
          </article>

        </section>

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
            <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              <DocumentIcon className="h-3.5 w-3.5" />
              Elenco avvisi
            </p>
            <p className="mt-3 text-lg font-semibold text-gray-900">Risultati del filtro corrente.</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
              Apri ogni avviso in modal per leggere importi, partite e particelle storicizzate del ruolo consortile senza perdere il contesto della lista.
            </p>
          </div>
          <div className="p-6">
            {error ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            ) : loading ? (
              <p className="text-sm text-gray-400">Caricamento...</p>
            ) : avvisi.length === 0 ? (
              <EmptyState
                icon={DocumentIcon}
                title="Nessun avviso trovato"
                description="Modifica i filtri o amplia il perimetro di ricerca per trovare avvisi coerenti con i parametri impostati."
              />
            ) : (
              <div className="space-y-3">
                {avvisi.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => setSelectedAvviso(a)}
                    className="group grid w-full gap-3 rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-[#c9d6cd] hover:shadow-sm md:grid-cols-[minmax(0,1fr),auto]"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-gray-900">
                          {a.display_name ?? a.nominativo_raw ?? "Avviso senza nominativo"}
                        </p>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${a.is_linked ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                          {a.is_linked ? "Collegato" : "Orfano"}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-xs leading-5 text-gray-500">
                        Anno {a.anno_tributario} · CNC {a.codice_cnc} · CF/P.IVA {a.codice_fiscale_raw ?? "—"} · Utenza {a.codice_utenza ?? "—"}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 justify-self-start md:justify-self-end">
                      <div className="text-right">
                        <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totale €</p>
                        <p className="mt-1 text-sm font-semibold text-gray-900">{formatEuro(a.importo_totale_euro)}</p>
                      </div>
                      <span className="text-sm text-gray-300 transition group-hover:text-[#1D4E35]">→</span>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {totalPages > 1 ? (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50"
                >
                  ← Precedente
                </button>
                <span className="text-sm text-gray-500">
                  Pagina {page} di {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50"
                >
                  Successiva →
                </button>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </RuoloModulePage>
  );
}

function RuoloAvvisiPageFallback() {
  return (
    <RuoloModulePage
      title="Avvisi Ruolo"
      description="Elenco degli avvisi consortili importati dal Ruolo."
      breadcrumb="Avvisi"
      requiredSection="ruolo.avvisi"
    >
      <div className="rounded-xl border border-gray-100 bg-white p-6 text-sm text-gray-500 shadow-sm">
        Caricamento avvisi...
      </div>
    </RuoloModulePage>
  );
}
