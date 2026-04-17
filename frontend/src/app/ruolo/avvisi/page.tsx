"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
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

  const anno = searchParams.get("anno") ? Number(searchParams.get("anno")) : undefined;
  const codice_fiscale = searchParams.get("cf") ?? undefined;
  const comune = searchParams.get("comune") ?? undefined;
  const codice_utenza = searchParams.get("utenza") ?? undefined;
  const unlinked = searchParams.get("unlinked") === "true";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  const [filterAnno, setFilterAnno] = useState(anno?.toString() ?? "");
  const [filterCf, setFilterCf] = useState(codice_fiscale ?? "");
  const [filterComune, setFilterComune] = useState(comune ?? "");
  const [filterUtenza, setFilterUtenza] = useState(codice_utenza ?? "");
  const [filterUnlinked, setFilterUnlinked] = useState(unlinked);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    listAvvisi(token, {
      anno,
      codice_fiscale,
      comune,
      codice_utenza,
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
  }, [token, anno, codice_fiscale, comune, codice_utenza, unlinked, page]);

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    const qs = new URLSearchParams();
    if (filterAnno) qs.set("anno", filterAnno);
    if (filterCf) qs.set("cf", filterCf);
    if (filterComune) qs.set("comune", filterComune);
    if (filterUtenza) qs.set("utenza", filterUtenza);
    if (filterUnlinked) qs.set("unlinked", "true");
    qs.set("page", "1");
    router.push(`/ruolo/avvisi?${qs}`);
  }

  function setPage(nextPage: number) {
    const qs = new URLSearchParams(searchParams.toString());
    qs.set("page", String(nextPage));
    router.push(`/ruolo/avvisi?${qs}`);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const exportUrl = buildExportCsvUrl({ anno, codice_fiscale, comune, codice_utenza, unlinked });

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
        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Consultazione avvisi
            </>
          }
          title="Ricerca, filtra e apri gli avvisi del ruolo consortile."
          description="Usa i filtri URL-driven per restringere il perimetro, controllare gli orfani anagrafici e passare dal cruscotto alla scheda puntuale senza perdere il contesto operativo."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={loading ? "Caricamento dataset" : `${total} avvisi nel risultato`}
                description={
                  anno
                    ? `Filtro attivo sull'anno ${anno}.`
                    : "Nessun filtro annuale attivo: stai consultando l'intero storico disponibile."
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

        <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
          <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <SearchIcon className="h-3.5 w-3.5" />
                Filtri ricerca
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Imposta il perimetro di consultazione.</p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                I filtri aggiornano la querystring, così puoi condividere la vista corrente o rientrare esattamente sullo stesso set di risultati.
              </p>
            </div>
            <div className="p-6">
              <form onSubmit={applyFilters} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Anno</span>
                  <input
                    type="number"
                    placeholder="Anno"
                    value={filterAnno}
                    onChange={(e) => setFilterAnno(e.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:border-[#1D4E35] focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">CF / P.IVA</span>
                  <input
                    type="text"
                    placeholder="CF / PIVA"
                    value={filterCf}
                    onChange={(e) => setFilterCf(e.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:border-[#1D4E35] focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Comune</span>
                  <input
                    type="text"
                    placeholder="Comune"
                    value={filterComune}
                    onChange={(e) => setFilterComune(e.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:border-[#1D4E35] focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Codice utenza</span>
                  <input
                    type="text"
                    placeholder="Cod. utenza"
                    value={filterUtenza}
                    onChange={(e) => setFilterUtenza(e.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:border-[#1D4E35] focus:outline-none"
                  />
                </label>
                <label className="flex items-center gap-3 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-700 md:col-span-2 xl:col-span-1">
                  <input
                    type="checkbox"
                    checked={filterUnlinked}
                    onChange={(e) => setFilterUnlinked(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Solo avvisi non collegati
                </label>
                <div className="flex items-end gap-3 md:col-span-2 xl:col-span-1">
                  <button
                    type="submit"
                    className="rounded-xl bg-[#1D4E35] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#163d29]"
                  >
                    Filtra
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFilterAnno("");
                      setFilterCf("");
                      setFilterComune("");
                      setFilterUtenza("");
                      setFilterUnlinked(false);
                      router.push("/ruolo/avvisi?page=1");
                    }}
                    className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2.5 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Reset
                  </button>
                </div>
              </form>
            </div>
          </article>

          <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <FolderIcon className="h-3.5 w-3.5" />
                Stato vista
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Lettura rapida del risultato corrente.</p>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Le mini-stat riassumono il peso economico e il livello di collegamento anagrafico della pagina selezionata.
              </p>
            </div>
            <div className="mt-6 grid gap-3">
              <ModuleWorkspaceMiniStat
                eyebrow="Anno filtro"
                value={anno ?? "Tutti"}
                description={anno ? "La lista è limitata all'anno tributario selezionato." : "La vista include tutte le annualità disponibili."}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Record in pagina"
                value={avvisi.length}
                description={loading ? "Il caricamento è ancora in corso." : `${total} record totali disponibili sul dataset.`}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Collegamento"
                value={`${linkedCount}/${avvisi.length || 0}`}
                description={orphanCount > 0 ? `${orphanCount} avvisi orfani nella pagina corrente.` : "Nessun orfano nei risultati attualmente visibili."}
                tone={orphanCount > 0 ? "warning" : "success"}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Totale economico"
                value={formatEuro(pageTotal)}
                description="Somma degli importi totali degli avvisi nella pagina corrente."
                compact
              />
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
              Apri la scheda puntuale di ogni avviso per leggere importi, partite e particelle storicizzate del ruolo consortile.
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
                  <Link
                    key={a.id}
                    href={`/ruolo/avvisi/${a.id}`}
                    className="group grid gap-3 rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4 transition hover:-translate-y-0.5 hover:border-[#c9d6cd] hover:shadow-sm md:grid-cols-[minmax(0,1fr),auto]"
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
                  </Link>
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
