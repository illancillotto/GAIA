"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { DocumentIcon, FolderIcon, RefreshIcon, SearchIcon, UserIcon } from "@/components/ui/icons";
import { getAnagraficaImportJobs, getAnagraficaStats, getAnagraficaSubjects } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaImportJob, AnagraficaStats, AnagraficaSubjectListItem } from "@/types/api";

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
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  return (
    <div className="page-stack">
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
        <MetricCard label="Documenti" value={stats.total_documents} sub={`${stats.documents_unclassified} non classificati`} />
        <MetricCard label="Da revisionare" value={stats.requires_review} sub="Soggetti con warning o classificazione incerta" variant={stats.requires_review > 0 ? "warning" : "success"} />
        <MetricCard label="Snapshot recenti" value={jobs.length} sub={`${jobs.filter((job) => job.status === "completed").length} completi`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
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
                <Link
                  key={subject.id}
                  href={`/anagrafica/${subject.id}`}
                  className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 transition hover:bg-gray-50"
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
                </Link>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
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
                <div key={job.job_id} className="rounded-lg border border-gray-100 px-4 py-3">
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

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Indicatori archivio</p>
          <p className="section-copy">Distribuzione sintetica dei soggetti per lettera di archivio.</p>
        </div>
        {Object.keys(stats.by_letter).length === 0 ? (
          <EmptyState icon={DocumentIcon} title="Nessuna distribuzione disponibile" description="La distribuzione per lettera apparirà dopo la creazione o l'import dei primi soggetti." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            {Object.entries(stats.by_letter)
              .slice(0, 12)
              .map(([letter, total]) => (
                <div key={letter} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-widest text-gray-400">{letter}</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{total}</p>
                </div>
              ))}
          </div>
        )}
      </article>
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
