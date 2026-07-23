"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ModuleWorkspaceHero, ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import {
  importTributiPayments,
  listTributiPaymentImportJobs,
  listTributiPaymentImportUnmatched,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiPaymentImportJobResponse,
  RuoloTributiPaymentImportUnmatchedItem,
} from "@/types/ruolo";

const DEFAULT_MAPPING = `{
  "codice_cnc": "Avviso",
  "anno_tributario": "Anno",
  "amount": "Importo pagato",
  "paid_at": "Data pagamento",
  "payment_reference": "Riferimento",
  "payment_method": "Metodo"
}`;

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatCount(value: number | null | undefined): string {
  return new Intl.NumberFormat("it-IT").format(value ?? 0);
}

function statusLabel(status: string): string {
  switch (status) {
    case "completed":
      return "Completato";
    case "failed":
      return "Fallito";
    case "running":
      return "In corso";
    default:
      return status;
  }
}

function statusClassName(status: string): string {
  if (status === "completed") return "bg-emerald-50 text-emerald-700";
  if (status === "failed") return "bg-rose-50 text-rose-700";
  return "bg-amber-50 text-amber-800";
}

export default function RuoloTributiImportPagamentiPage() {
  const [token, setToken] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mappingText, setMappingText] = useState(DEFAULT_MAPPING);
  const [jobs, setJobs] = useState<RuoloTributiPaymentImportJobResponse[]>([]);
  const [selectedJob, setSelectedJob] = useState<RuoloTributiPaymentImportJobResponse | null>(null);
  const [unmatched, setUnmatched] = useState<RuoloTributiPaymentImportUnmatchedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    listTributiPaymentImportJobs(token, 1, 12)
      .then((response) => {
        if (cancelled) return;
        setJobs(response.items);
        setSelectedJob((current) => current ?? response.items[0] ?? null);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Errore caricamento job import pagamenti");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !selectedJob) {
      setUnmatched([]);
      return;
    }
    let cancelled = false;
    listTributiPaymentImportUnmatched(token, selectedJob.id)
      .then((response) => {
        if (!cancelled) setUnmatched(response.items);
      })
      .catch(() => {
        if (!cancelled) setUnmatched([]);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedJob, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !file) return;
    setUploading(true);
    setError(null);
    try {
      const trimmedMapping = mappingText.trim();
      let mapping: Record<string, string> | undefined;
      if (trimmedMapping) {
        try {
          mapping = JSON.parse(trimmedMapping) as Record<string, string>;
        } catch {
          throw new Error("Mapping colonne non valido");
        }
      }
      const result = await importTributiPayments(token, file, mapping);
      setSelectedJob(result);
      setJobs((current) => [result, ...current.filter((job) => job.id !== result.id)].slice(0, 12));
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore import pagamenti CapaciTas");
    } finally {
      setUploading(false);
    }
  }

  return (
    <RuoloModulePage
      title="Import Pagamenti Tributi"
      description="Carica l'export pagamenti CapaciTas e riconcilia le righe sugli avvisi a ruolo."
      breadcrumb="Import pagamenti"
      requiredSection="ruolo.tributi.import_payments"
    >
      <div className="space-y-6">
        <ModuleWorkspaceHero
          badge="CapaciTas payments"
          title="Import pagamenti con matching controllato"
          description="GAIA abbina prima il codice avviso CNC e poi codice utenza + annualita. Le righe ambigue o non riconosciute restano nel report del job, senza creare pagamenti forzati."
          actions={(
            <Link className="btn-secondary" href="/ruolo/tributi">
              Torna ai tributi
            </Link>
          )}
        />

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
          <form className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.75fr)]" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <p className="section-title">File pagamenti</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-900">Upload CSV, XLSX o XLSM</h2>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  Il file deve avere una riga intestazione. Il mapping e opzionale se le colonne hanno nomi riconoscibili.
                </p>
              </div>
              <input
                aria-label="File pagamenti CapaciTas"
                className="block w-full rounded-2xl border border-[#d8dfd3] bg-[#fbfcf8] px-4 py-3 text-sm"
                type="file"
                accept=".csv,.txt,.xlsx,.xlsm"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              {file ? <p className="text-sm font-medium text-[#1D4E35]">Selezionato: {file.name}</p> : null}
              {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}
              <button className="btn-primary" type="submit" disabled={!file || !token || uploading}>
                {uploading ? "Import in corso..." : "Avvia import pagamenti"}
              </button>
            </div>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Mapping colonne opzionale</span>
              <textarea
                className="mt-2 min-h-[240px] w-full rounded-2xl border border-[#d8dfd3] bg-[#fbfcf8] p-4 font-mono text-xs text-gray-800 outline-none focus:border-[#8CB39D]"
                value={mappingText}
                onChange={(event) => setMappingText(event.target.value)}
              />
            </label>
          </form>
        </section>

        {selectedJob ? (
          <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="section-title">Ultimo job</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-900">{selectedJob.filename ?? "Import pagamenti"}</h2>
                <p className="mt-1 text-sm text-gray-500">Creato il {formatDateTime(selectedJob.created_at)}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClassName(selectedJob.status)}`}>
                {statusLabel(selectedJob.status)}
              </span>
            </div>
            <div className="mt-5">
              <ModuleWorkspaceKpiRow>
                <ModuleWorkspaceKpiTile label="Righe" value={formatCount(selectedJob.records_total)} hint="lette dal file" />
                <ModuleWorkspaceKpiTile label="Importate" value={formatCount(selectedJob.records_imported)} hint="pagamenti creati" variant="emerald" />
                <ModuleWorkspaceKpiTile label="Non abbinate" value={formatCount(selectedJob.records_unmatched)} hint="da verificare" variant="amber" />
                <ModuleWorkspaceKpiTile label="Errori" value={formatCount(selectedJob.records_errors)} hint="righe non valide" />
              </ModuleWorkspaceKpiRow>
            </div>
            {selectedJob.error_detail ? <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{selectedJob.error_detail}</p> : null}
          </section>
        ) : null}

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <p className="section-title">Storico import</p>
            {loading ? (
              <p className="mt-4 text-sm text-gray-500">Caricamento job...</p>
            ) : jobs.length === 0 ? (
              <EmptyState icon={DocumentIcon} title="Nessun import pagamenti" description="Carica il primo export CapaciTas per popolare lo storico." />
            ) : (
              <div className="mt-4 space-y-3">
                {jobs.map((job) => (
                  <button
                    key={job.id}
                    type="button"
                    className={`w-full rounded-2xl border p-4 text-left transition ${selectedJob?.id === job.id ? "border-[#1D4E35] bg-[#f4faf6]" : "border-[#e5ebe1] bg-white hover:border-[#8CB39D]"}`}
                    onClick={() => setSelectedJob(job)}
                  >
                    <span className="block text-sm font-semibold text-gray-900">{job.filename ?? job.id}</span>
                    <span className="mt-1 block text-xs text-gray-500">
                      {formatDateTime(job.created_at)} · {formatCount(job.records_imported)} importate · {formatCount((job.records_unmatched ?? 0) + (job.records_errors ?? 0))} da verificare
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <p className="section-title">Righe da verificare</p>
            {unmatched.length === 0 ? (
              <EmptyState icon={DocumentIcon} title="Nessuna anomalia nel job selezionato" description="Le righe importate sono state abbinate oppure non e ancora stato selezionato un job." />
            ) : (
              <div className="mt-4 max-h-[520px] overflow-auto rounded-2xl border border-[#edf1e9]">
                <table className="min-w-full divide-y divide-[#edf1e9] text-sm">
                  <thead className="bg-[#fbfcf8] text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Riga</th>
                      <th className="px-4 py-3">Motivo</th>
                      <th className="px-4 py-3">Dati raw</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#edf1e9]">
                    {unmatched.map((item) => (
                      <tr key={`${item.row_number}-${item.reason}`}>
                        <td className="px-4 py-3 font-mono text-xs">{item.row_number}</td>
                        <td className="px-4 py-3 font-medium text-amber-800">{item.reason}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-600">{JSON.stringify(item.raw)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>
    </RuoloModulePage>
  );
}
