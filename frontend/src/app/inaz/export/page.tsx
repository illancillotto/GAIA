"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import { exportInazXlsm, listInazCollaborators } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazCollaborator } from "@/types/api";

function monthStartInputValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

export default function InazExportPage() {
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [periodStart, setPeriodStart] = useState(monthStartInputValue());
  const [employeeKind, setEmployeeKind] = useState("AVVENTIZI");
  const [templatePath, setTemplatePath] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    listInazCollaborators(token, { page: 1, pageSize: 200 })
      .then((response) => setCollaborators(response.items))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"))
      .finally(() => setIsLoading(false));
  }, []);

  const mappedCount = useMemo(() => collaborators.filter((item) => item.application_user_id != null).length, [collaborators]);

  async function handleExport() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsExporting(true);
    setError(null);
    setSuccess(null);
    try {
      const blob = await exportInazXlsm(token, {
        periodStart,
        collaboratorIds: selectedIds,
        employeeKind,
        templatePath: templatePath.trim() || undefined,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `inaz_giornaliere_${periodStart}.xlsm`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setSuccess("Export XLSM generato e download avviato.");
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Errore export XLSM");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <ProtectedPage
      title="Export Inaz"
      description="Generazione file giornaliere XLSM."
      breadcrumb="Inaz"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Export giornaliere</>}
          title="Genera il file XLSM dalle giornaliere Inaz persistite in GAIA."
          description="Seleziona il mese, limita l'export a uno o piu collaboratori e, se serve, indica un template `.xlsm` alternativo. Il backend preserva le macro del file sorgente."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={templatePath.trim() ? "Template personalizzato" : "Template di default"}
                description={templatePath.trim() || "Verrà usato il template standard configurato lato backend."}
                tone="info"
              />
              <ModuleWorkspaceNoticeCard
                title={selectedIds.length > 0 ? "Export filtrato" : "Export completo"}
                description={
                  selectedIds.length > 0
                    ? `${selectedIds.length} collaboratori selezionati per il download.`
                    : "Nessun filtro collaboratore: il backend includera tutti i collaboratori con giornaliere nel mese scelto."
                }
                tone={selectedIds.length > 0 ? "warning" : "success"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Collaboratori" value={collaborators.length} hint="Dataset disponibile" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Collegati a application_users" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Selezionati" value={selectedIds.length || "Tutti"} hint="Ambito export" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="panel-card space-y-5">
          <div>
            <p className="section-title">Parametri export</p>
            <p className="section-copy">Configura il file da generare e avvia il download direttamente dal backend.</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block text-sm font-medium text-gray-700">
              Mese di riferimento
              <input className="form-control mt-1" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Tipo personale
              <input className="form-control mt-1" value={employeeKind} onChange={(event) => setEmployeeKind(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Template XLSM opzionale
              <input className="form-control mt-1" value={templatePath} onChange={(event) => setTemplatePath(event.target.value)} placeholder="/percorso/template.xlsm" />
            </label>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento collaboratori...</p>
          ) : collaborators.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun collaboratore importato" description="Importa prima un file JSON Inaz per poter esportare il mese." />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-gray-700">Collaboratori inclusi</p>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" onClick={() => setSelectedIds(collaborators.map((item) => item.id))}>
                    Seleziona tutti
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => setSelectedIds([])}>
                    Deseleziona
                  </button>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {collaborators.map((collaborator) => {
                  const isSelected = selectedIds.includes(collaborator.id);
                  return (
                    <label key={collaborator.id} className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(event) =>
                          setSelectedIds((current) =>
                            event.target.checked ? [...current, collaborator.id] : current.filter((item) => item !== collaborator.id),
                          )
                        }
                      />
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900">{collaborator.name}</p>
                        <p className="text-xs text-gray-500">
                          Matricola {collaborator.employee_code} · {collaborator.company_code ?? "n/d"} · {collaborator.application_user_id ? "mappato" : "non mappato"}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button className="btn-primary" type="button" onClick={() => void handleExport()} disabled={isExporting || !periodStart}>
              {isExporting ? "Generazione..." : "Scarica XLSM"}
            </button>
          </div>
        </section>
      </div>
    </ProtectedPage>
  );
}
