"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useState } from "react";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { FolderIcon, RefreshIcon, SearchIcon, UserIcon } from "@/components/ui/icons";
import { getAnagraficaDocumentSummary, getAnagraficaImportJobs, getAnagraficaStats, getAnagraficaSubjects, searchAnagraficaSubjects } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaDocumentSummary, AnagraficaImportJob, AnagraficaStats, AnagraficaSubjectListItem } from "@/types/api";

const emptyStats: AnagraficaStats = {
  total_subjects: 0,
  total_persons: 0,
  total_companies: 0,
  total_unknown: 0,
  total_documents: 0,
  requires_review: 0,
  active_subjects: 0,
  inactive_subjects: 0,
  documents_unclassified: 0,
  by_letter: {},
};

function badgeTone(value: string): string {
  switch (value) {
    case "person":
    case "active":
    case "completed":
      return "bg-emerald-50 text-emerald-700";
    case "company":
      return "bg-sky-50 text-sky-700";
    case "inactive":
    case "failed":
      return "bg-rose-50 text-rose-700";
    default:
      return "bg-amber-50 text-amber-700";
  }
}

function DashboardContent({ token }: { token: string }) {
  const [stats, setStats] = useState<AnagraficaStats>(emptyStats);
  const [subjects, setSubjects] = useState<AnagraficaSubjectListItem[]>([]);
  const [jobs, setJobs] = useState<AnagraficaImportJob[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<AnagraficaSubjectListItem[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSubject, setSelectedSubject] = useState<AnagraficaSubjectListItem | null>(null);
  const [documentSummary, setDocumentSummary] = useState<AnagraficaDocumentSummary | null>(null);
  const [isDocumentSummaryOpen, setIsDocumentSummaryOpen] = useState(false);
  const [isLoadingDocumentSummary, setIsLoadingDocumentSummary] = useState(false);
  const [documentSummaryError, setDocumentSummaryError] = useState<string | null>(null);
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const normalizedSearchTerm = deferredSearchTerm.trim();
  const canSearch = normalizedSearchTerm.length >= 3;

  useEffect(() => {
    async function loadData() {
      try {
        const [statsResponse, subjectsResponse, jobsResponse] = await Promise.all([
          getAnagraficaStats(token),
          getAnagraficaSubjects(token, { pageSize: 6 }),
          getAnagraficaImportJobs(token),
        ]);
        setStats(statsResponse);
        setSubjects(subjectsResponse.items);
        setJobs(jobsResponse.slice(0, 5));
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento modulo");
      } finally {
        setIsLoading(false);
      }
    }

    void loadData();
  }, [token]);

  useEffect(() => {
    async function loadSearchResults() {
      if (!canSearch) {
        setSearchResults([]);
        setSearchTotal(0);
        setSearchError(null);
        setIsSearching(false);
        return;
      }

      setIsSearching(true);
      try {
        const response = await searchAnagraficaSubjects(token, normalizedSearchTerm, 12);
        setSearchResults(response.items);
        setSearchTotal(response.total);
        setSearchError(null);
      } catch (error) {
        setSearchError(error instanceof Error ? error.message : "Errore durante la ricerca");
        setSearchResults([]);
        setSearchTotal(0);
      } finally {
        setIsSearching(false);
      }
    }

    void loadSearchResults();
  }, [canSearch, normalizedSearchTerm, token]);

  async function handleOpenDocumentSummary() {
    setIsDocumentSummaryOpen(true);
    if (documentSummary || isLoadingDocumentSummary) {
      return;
    }

    setIsLoadingDocumentSummary(true);
    setDocumentSummaryError(null);
    try {
      const response = await getAnagraficaDocumentSummary(token);
      setDocumentSummary(response);
    } catch (error) {
      setDocumentSummaryError(error instanceof Error ? error.message : "Errore caricamento riepilogo documenti");
    } finally {
      setIsLoadingDocumentSummary(false);
    }
  }

  return (
    <div className="page-stack">
      {selectedSubject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
          <div className="flex h-full max-h-[94vh] w-full max-w-6xl flex-col rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
              <div className="min-w-0">
                <p className="section-title">Dettaglio soggetto</p>
                <p className="mt-1 truncate text-sm text-gray-500">{selectedSubject.display_name}</p>
              </div>
              <div className="flex items-center gap-3">
                <Link className="btn-secondary" href={`/anagrafica/${selectedSubject.id}`} target="_blank">
                  Apri pagina
                </Link>
                <button className="btn-secondary" type="button" onClick={() => setSelectedSubject(null)}>
                  Chiudi
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden p-4">
              <iframe
                key={selectedSubject.id}
                src={`/anagrafica/${selectedSubject.id}?embedded=1`}
                title={`Dettaglio ${selectedSubject.display_name}`}
                className="h-full w-full rounded-xl border border-gray-200 bg-white"
              />
            </div>
          </div>
        </div>
      ) : null}

      {isDocumentSummaryOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
          <div className="flex h-full max-h-[92vh] w-full max-w-4xl flex-col rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
              <div>
                <p className="section-title">Riepilogo documenti</p>
                <p className="mt-1 text-sm text-gray-500">Dettaglio classificazione e ultimi documenti non classificati.</p>
              </div>
              <div className="flex items-center gap-3">
                <Link className="btn-secondary" href="/anagrafica/subjects" target="_blank">
                  Apri pagina
                </Link>
                <button className="btn-secondary" type="button" onClick={() => setIsDocumentSummaryOpen(false)}>
                  Chiudi
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {isLoadingDocumentSummary ? <p className="text-sm text-gray-500">Caricamento riepilogo documenti...</p> : null}
              {documentSummaryError ? <p className="text-sm text-red-600">{documentSummaryError}</p> : null}
              {!isLoadingDocumentSummary && !documentSummaryError && documentSummary ? (
                <div className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                      <p className="text-xs uppercase tracking-widest text-gray-400">Totale documenti</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{documentSummary.total_documents}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                      <p className="text-xs uppercase tracking-widest text-gray-400">Classificati</p>
                      <p className="mt-2 text-2xl font-semibold text-emerald-700">{documentSummary.classified_documents}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                      <p className="text-xs uppercase tracking-widest text-gray-400">Non classificati</p>
                      <p className="mt-2 text-2xl font-semibold text-amber-600">{documentSummary.documents_unclassified}</p>
                    </div>
                  </div>

                  <div>
                    <p className="section-title">Classificazione per categoria</p>
                    <div className="mt-4 space-y-3">
                      {documentSummary.by_doc_type.map((bucket) => (
                        <div key={bucket.doc_type} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
                          <span className="text-sm font-medium text-gray-900">{bucket.doc_type}</span>
                          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">{bucket.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="section-title">Ultimi non classificati</p>
                    {documentSummary.recent_unclassified.length === 0 ? (
                      <p className="mt-4 text-sm text-gray-500">Nessun documento non classificato.</p>
                    ) : (
                      <div className="mt-4 space-y-3">
                        {documentSummary.recent_unclassified.map((item) => (
                          <button
                            key={item.document_id}
                            type="button"
                            onClick={() => {
                              setIsDocumentSummaryOpen(false);
                              setSelectedSubject({
                                id: item.subject_id,
                                subject_type: "unknown",
                                status: "active",
                                source_name_raw: item.subject_display_name,
                                display_name: item.subject_display_name,
                                codice_fiscale: null,
                                partita_iva: null,
                                nas_folder_path: null,
                                nas_folder_letter: null,
                                requires_review: true,
                                imported_at: null,
                                document_count: 0,
                                created_at: item.created_at,
                                updated_at: item.created_at,
                              });
                            }}
                            className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
                          >
                            <div>
                              <p className="text-sm font-medium text-gray-900">{item.filename}</p>
                              <p className="mt-1 text-xs text-gray-500">{item.subject_display_name}</p>
                            </div>
                            <span className="text-xs text-gray-400">{formatDateTime(item.created_at)}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Registro soggetti del Consorzio, con snapshot archivio NAS, classificazione documentale e ricerca operativa.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary" href="/anagrafica/subjects">
            <SearchIcon className="h-4 w-4" />
            Apri soggetti
          </Link>
          <Link className="btn-primary" href="/anagrafica/import">
            <RefreshIcon className="h-4 w-4" />
            Crea snapshot
          </Link>
        </div>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Soggetti totali" value={stats.total_subjects} sub={`${stats.total_persons} PF · ${stats.total_companies} PG`} />
        <button
          type="button"
          className="group rounded-[28px] text-left outline-none transition hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-[#1D4E35]/30"
          onClick={() => void handleOpenDocumentSummary()}
          aria-label="Apri riepilogo documenti"
        >
          <div className="relative">
            <MetricCard label="Documenti" value={stats.total_documents} sub={`${stats.documents_unclassified} non classificati`} />
            <span className="absolute right-5 top-4 rounded-full bg-[#1D4E35]/8 px-2.5 py-1 text-[11px] font-medium text-[#1D4E35] transition group-hover:bg-[#1D4E35] group-hover:text-white">
              Apri dettaglio
            </span>
          </div>
        </button>
        <MetricCard label="Da revisionare" value={stats.requires_review} sub="Soggetti con warning o classificazione incerta" variant={stats.requires_review > 0 ? "warning" : "success"} />
        <MetricCard label="Snapshot recenti" value={jobs.length} sub={`${jobs.filter((job) => job.status === "completed").length} completi`} />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Ricerca soggetti</p>
            <p className="section-copy">Inserisci almeno 3 lettere del nome, cognome o ragione sociale per trovare subito i record.</p>
          </div>
          <Link href="/anagrafica/subjects" className="text-sm font-medium text-[#1D4E35]">
            Ricerca avanzata
          </Link>
        </div>

        <label className="block">
          <span className="sr-only">Cerca soggetto</span>
          <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
            <SearchIcon className="h-5 w-5 text-gray-400" />
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Es. ROS, BIA, IMM..."
              className="w-full border-0 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
            />
          </div>
        </label>

        <div className="mt-4">
          {searchError ? (
            <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{searchError}</div>
          ) : normalizedSearchTerm.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Ricerca pronta" description="Digita le prime 3 lettere per vedere i soggetti corrispondenti." />
          ) : !canSearch ? (
            <EmptyState icon={SearchIcon} title="Inserisci almeno 3 lettere" description="Appena raggiungi 3 caratteri il sistema lancia la ricerca." />
          ) : isSearching ? (
            <p className="text-sm text-gray-500">Ricerca in corso per “{normalizedSearchTerm}”.</p>
          ) : searchResults.length === 0 ? (
            <EmptyState icon={SearchIcon} title="Nessun risultato" description={`Nessun soggetto trovato per “${normalizedSearchTerm}”.`} />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-gray-500">
                  {searchTotal} risultati per <span className="font-medium text-gray-800">“{normalizedSearchTerm}”</span>
                </p>
                {searchTotal > searchResults.length ? (
                  <p className="text-xs text-gray-400">Mostrati i primi {searchResults.length}</p>
                ) : null}
              </div>

              {searchResults.map((subject) => (
                <button
                  key={subject.id}
                  type="button"
                  onClick={() => setSelectedSubject(subject)}
                  className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{subject.display_name}</p>
                      <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${badgeTone(subject.subject_type)}`}>
                        {subject.subject_type.toUpperCase()}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {subject.codice_fiscale || subject.partita_iva || "Identificativo non disponibile"} · {subject.document_count} documenti · {subject.nas_folder_letter || "?"}
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${subject.requires_review ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-600"}`}>
                    {subject.requires_review ? "Review" : "OK"}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </article>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.9fr]">
        <article className="panel-card p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Soggetti recenti</p>
              <p className="section-copy">Ultimi record creati o aggiornati nel dominio Anagrafica.</p>
            </div>
            <Link href="/anagrafica/subjects" className="text-sm font-medium text-[#1D4E35]">
              Lista completa
            </Link>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento soggetti in corso.</p>
          ) : subjects.length === 0 ? (
            <EmptyState icon={UserIcon} title="Nessun soggetto disponibile" description="Crea uno snapshot dell’archivio NAS o inserisci una scheda manuale per iniziare." />
          ) : (
            <div className="space-y-3">
              {subjects.map((subject) => (
                <button
                  key={subject.id}
                  type="button"
                  onClick={() => setSelectedSubject(subject)}
                  className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-3 py-2.5 text-left transition hover:bg-gray-50"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{subject.display_name}</p>
                      <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${badgeTone(subject.subject_type)}`}>
                        {subject.subject_type.toUpperCase()}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {subject.codice_fiscale || subject.partita_iva || "Identificativo non disponibile"} · {subject.document_count} documenti · {subject.nas_folder_letter || "?"}
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${subject.requires_review ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-600"}`}>
                    {subject.requires_review ? "Review" : "OK"}
                  </span>
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Snapshot recenti</p>
              <p className="section-copy">Storico breve delle acquisizioni di staging archivio.</p>
            </div>
            <Link href="/anagrafica/import" className="text-sm font-medium text-[#1D4E35]">
              Apri wizard
            </Link>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento import in corso.</p>
          ) : jobs.length === 0 ? (
            <EmptyState icon={FolderIcon} title="Nessuno snapshot disponibile" description="Le acquisizioni di staging compariranno qui dopo il primo salvataggio." />
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.job_id} className="rounded-lg border border-gray-100 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-gray-900">{job.letter === "ALL" ? "Archivio completo" : `Lettera ${job.letter || "?"}`}</p>
                    <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${badgeTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    {job.imported_ok} importati · {job.imported_errors} errori · {job.warning_count} warning
                  </p>
                  <p className="mt-1 text-xs text-gray-400">{formatDateTime(job.completed_at || job.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </div>
  );
}

export default function AnagraficaPage() {
  return (
    <AnagraficaModulePage
      title="Dashboard"
      description="Vista sintetica del registro soggetti, dello stato import archivio e della qualità del dato Anagrafica."
    >
      {({ token }) => <DashboardContent token={token} />}
    </AnagraficaModulePage>
  );
}
