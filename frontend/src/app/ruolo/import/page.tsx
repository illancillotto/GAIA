"use client";

import { useEffect, useRef, useState } from "react";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getStoredAccessToken } from "@/lib/auth";
import { getImportJob, listImportJobs, uploadRuoloFile } from "@/lib/ruolo-api";
import type { RuoloImportJobResponse } from "@/types/ruolo";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export default function RuoloImportPage() {
  const [token, setToken] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [anno, setAnno] = useState<number>(new Date().getFullYear());
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [warningMsg, setWarningMsg] = useState<string | null>(null);
  const [jobs, setJobs] = useState<RuoloImportJobResponse[]>([]);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    listImportJobs(token, undefined, 1, 20)
      .then((r) => setJobs(r.items))
      .catch(console.error);
  }, [token]);

  useEffect(() => {
    if (!pollingJobId || !token) return;
    pollRef.current = setInterval(() => {
      getImportJob(token, pollingJobId)
        .then((job) => {
          setJobs((prev) => prev.map((j) => (j.id === job.id ? job : j)));
          if (job.status === "completed" || job.status === "failed") {
            clearInterval(pollRef.current!);
            setPollingJobId(null);
          }
        })
        .catch(console.error);
    }, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pollingJobId, token]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !token) return;
    setUploading(true);
    setUploadError(null);
    setWarningMsg(null);
    try {
      const result = await uploadRuoloFile(token, file, anno);
      if (result.warning_existing) {
        setWarningMsg(
          `Attenzione: esistono già ${result.existing_count} avvisi per l'anno ${anno}. I dati verranno aggiornati.`,
        );
      }
      const newJob: RuoloImportJobResponse = {
        id: result.job_id,
        anno_tributario: result.anno_tributario,
        filename: file.name,
        status: result.status,
        started_at: new Date().toISOString(),
        finished_at: null,
        total_partite: null,
        records_imported: null,
        records_skipped: null,
        records_errors: null,
        error_detail: null,
        triggered_by: null,
        params_json: null,
        created_at: new Date().toISOString(),
      };
      setJobs((prev) => [newJob, ...prev]);
      setPollingJobId(result.job_id);
      setFile(null);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Errore durante l'upload");
    } finally {
      setUploading(false);
    }
  }

  return (
    <RuoloModulePage
      title="Import Ruolo"
      description="Carica un file Ruolo consortile per avviare l'import."
      breadcrumb="Import"
      requiredSection="ruolo.import"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <div>
          <h2 className="mb-1 text-xl font-semibold text-gray-800">Import file Ruolo</h2>
          <p className="text-sm text-gray-500">
            Carica un file <code>.dmp</code> o PDF testuale generato da Capacitas.
          </p>
        </div>

        {/* Upload form */}
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <form onSubmit={handleUpload} className="space-y-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700" htmlFor="anno">
                  Anno tributario
                </label>
                <input
                  id="anno"
                  type="number"
                  min={1990}
                  max={2100}
                  value={anno}
                  onChange={(e) => setAnno(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 focus:border-[#1D4E35] focus:outline-none focus:ring-1 focus:ring-[#1D4E35]"
                  required
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700" htmlFor="file">
                  File (.dmp o .pdf)
                </label>
                <input
                  id="file"
                  type="file"
                  accept=".dmp,.pdf,.txt"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-[#EAF3E8] file:px-3 file:py-1 file:text-xs file:font-medium file:text-[#1D4E35]"
                  required
                />
              </div>
            </div>

            {warningMsg && (
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
                ⚠ {warningMsg}
              </div>
            )}

            {uploadError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {uploadError}
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={uploading || !file}
                className="rounded-lg bg-[#1D4E35] px-5 py-2 text-sm font-medium text-white transition hover:bg-[#163d29] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {uploading ? "Invio in corso..." : "Avvia import"}
              </button>
            </div>
          </form>
        </div>

        {/* Jobs history */}
        {jobs.length > 0 && (
          <div>
            <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">
              Cronologia import
            </h3>
            <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    <th className="px-4 py-3">Anno</th>
                    <th className="px-4 py-3">File</th>
                    <th className="px-4 py-3">Stato</th>
                    <th className="px-4 py-3">Importati</th>
                    <th className="px-4 py-3">Saltati</th>
                    <th className="px-4 py-3">Errori</th>
                    <th className="px-4 py-3">Data</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{job.anno_tributario}</td>
                      <td className="max-w-[180px] truncate px-4 py-3 text-gray-500" title={job.filename ?? ""}>
                        {job.filename ?? "—"}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 text-gray-700">{job.records_imported ?? "—"}</td>
                      <td className="px-4 py-3 text-gray-500">{job.records_skipped ?? "—"}</td>
                      <td className="px-4 py-3">
                        {job.records_errors != null && job.records_errors > 0 ? (
                          <span className="text-red-600">{job.records_errors}</span>
                        ) : (
                          <span className="text-gray-400">{job.records_errors ?? "—"}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {new Date(job.started_at).toLocaleDateString("it-IT")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </RuoloModulePage>
  );
}
